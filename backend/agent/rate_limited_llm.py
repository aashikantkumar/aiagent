"""
Rate-limited LLM wrapper for Groq free-tier.

Wraps any LangChain chat model and adds:
  1. Pre-request key acquisition from GroqKeyPool
  2. Automatic retry with key rotation on 429 errors
  3. Exponential backoff with jitter
  4. Token usage tracking back to the pool
"""
from __future__ import annotations

import asyncio
import random
import re
from typing import Any, Iterator, List, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun, AsyncCallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

from core.logger import get_logger

logger = get_logger(__name__)

# Regex to extract retry-after from error messages
RETRY_AFTER_RE = re.compile(r"try again in (\d+(?:\.\d+)?)(ms|s|m)", re.IGNORECASE)


def _parse_retry_after(error_msg: str) -> float:
    """Extract retry-after duration from a Groq 429 error message."""
    match = RETRY_AFTER_RE.search(str(error_msg))
    if match:
        value = float(match.group(1))
        unit = match.group(2).lower()
        if unit == "ms":
            return value / 1000
        if unit == "m":
            return value * 60
        return value  # seconds
    return 60.0  # default 60s cooldown


def _estimate_tokens(messages: List[BaseMessage]) -> int:
    """Rough token estimate (4 chars ≈ 1 token)."""
    total_chars = sum(len(m.content) if isinstance(m.content, str) else 0 for m in messages)
    return max(total_chars // 4, 1)


class RateLimitedGroqLLM(BaseChatModel):
    """
    A LangChain-compatible chat model that wraps Groq calls with:
      - Automatic key rotation from GroqKeyPool
      - Retry on 429 with exponential backoff
      - Token usage tracking

    Usage:
        from agent.rate_limited_llm import RateLimitedGroqLLM
        llm = RateLimitedGroqLLM(
            model="groq/llama-3.3-70b-versatile",
            temperature=0.2,
        )
        response = await llm.ainvoke([HumanMessage(content="Hello")])
    """

    model: str = "groq/llama-3.3-70b-versatile"
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    max_retries: int = 10  # Total retries across all keys
    base_delay: float = 2.0  # Initial backoff delay in seconds
    max_delay: float = 120.0  # Maximum backoff delay

    class Config:
        arbitrary_types_allowed = True

    @property
    def _llm_type(self) -> str:
        return "rate_limited_groq"

    @property
    def _identifying_params(self) -> dict:
        return {"model": self.model, "temperature": self.temperature}

    def _create_inner_llm(self, api_key: str) -> BaseChatModel:
        """Create a fresh ChatLiteLLM instance with the given API key."""
        from langchain_community.chat_models import ChatLiteLLM

        params: dict[str, Any] = {
            "model": self.model,
            "temperature": self.temperature,
            "api_key": api_key,
            "max_retries": 0,  # We handle retries ourselves
            "timeout": 180,  # 3 minute timeout per request
        }
        if self.max_tokens is not None:
            params["max_tokens"] = self.max_tokens
        return ChatLiteLLM(**params)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Synchronous generation — uses asyncio.run for the async path."""
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # We're already in an async context — create a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    self._agenerate(messages, stop=stop, run_manager=None, **kwargs),
                )
                return future.result()
        else:
            return asyncio.run(
                self._agenerate(messages, stop=stop, run_manager=None, **kwargs)
            )

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        Async generation with automatic key rotation and retry logic.

        Flow:
          1. Acquire a key from the pool
          2. Try the request
          3a. On success → release key with token count → return
          3b. On 429 → report to pool → acquire next key → retry
          3c. On other error → report → retry with backoff
        """
        from agent.groq_key_pool import get_groq_pool

        pool = get_groq_pool()
        estimated_input_tokens = _estimate_tokens(messages)
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries):
            current_key: Optional[str] = None
            try:
                # 1. Acquire a key
                current_key = await pool.acquire(model=self.model)

                # 2. Create the LLM with this key
                inner_llm = self._create_inner_llm(current_key)

                # 3. Make the request
                result = await inner_llm.agenerate([messages], stop=stop, **kwargs)
                response = result.generations[0][0]

                # 4. Estimate tokens used and release the key
                output_tokens = len(response.text) // 4 if response.text else 0
                total_tokens = estimated_input_tokens + output_tokens
                pool.release(current_key, tokens_used=total_tokens)

                logger.info(
                    "groq_request_success",
                    attempt=attempt + 1,
                    key_suffix=f"...{current_key[-4:]}",
                    model=self.model,
                    tokens_estimated=total_tokens,
                )

                return ChatResult(
                    generations=[ChatGeneration(message=AIMessage(content=response.text))]
                )

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Check if it's a rate limit error (429)
                is_rate_limit = any(
                    indicator in error_str
                    for indicator in [
                        "429",
                        "rate_limit",
                        "rate limit",
                        "too many requests",
                        "ratelimit",
                        "quota",
                    ]
                )

                if is_rate_limit and current_key:
                    retry_after = _parse_retry_after(str(e))
                    pool.report_rate_limit(current_key, retry_after=retry_after)
                    logger.warning(
                        "groq_rate_limit_hit",
                        attempt=attempt + 1,
                        key_suffix=f"...{current_key[-4:]}",
                        retry_after=retry_after,
                        remaining_keys=pool.size - 1,
                    )
                    # Small delay before trying next key
                    await asyncio.sleep(min(1.0, retry_after / 10))
                    continue

                # Non-rate-limit error — backoff and retry
                if current_key:
                    pool.report_error(current_key)

                delay = min(
                    self.base_delay * (2 ** attempt) + random.uniform(0, 1),
                    self.max_delay,
                )
                logger.error(
                    "groq_request_error",
                    attempt=attempt + 1,
                    error=str(e)[:200],
                    backoff_seconds=round(delay, 1),
                )
                await asyncio.sleep(delay)

        # All retries exhausted
        pool_stats = pool.get_stats()
        logger.error(
            "groq_all_retries_exhausted",
            max_retries=self.max_retries,
            pool_stats=pool_stats,
        )
        raise RuntimeError(
            f"Groq API call failed after {self.max_retries} attempts across "
            f"{pool.size} API keys. Last error: {last_error}"
        )
