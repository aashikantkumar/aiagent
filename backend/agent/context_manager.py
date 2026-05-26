"""
Token & Context Management — prevents context overflow for all LLM providers.

Architecture (from AUTONOMOUS_AI_AGENT_ARCHITECTURE.md §4):
  - Token counting via tiktoken (OpenAI/Groq) or character estimation (Ollama)
  - Budget-based allocation across system prompt, tools, workspace, conversation
  - Intelligent truncation: keeps recent messages, summarizes older ones
  - Model-aware limits for small-context local models (8K Ollama)
"""
from __future__ import annotations

import re
from typing import Dict, List, Optional, TYPE_CHECKING

from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage

from core.logger import get_logger

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel

logger = get_logger(__name__)


# ── Model context limits ───────────────────────────────────────────────

MODEL_CONTEXT_LIMITS: Dict[str, int] = {
    # Ollama / local models
    "llama3.1:8b": 8_192,
    "llama3.1:70b": 128_000,
    "qwen2.5-coder:7b": 8_192,
    "qwen2.5-coder:32b": 32_768,
    "deepseek-coder:6.7b": 16_384,
    "codellama:13b": 16_384,
    "mistral:7b": 8_192,
    # Cloud models
    "gpt-4": 8_192,
    "gpt-4o": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-3.5-turbo": 16_385,
    "claude-3-5-sonnet-20241022": 200_000,
    "claude-3-opus-20240229": 200_000,
    # Groq / cloud models
    "groq/llama-3.3-70b-versatile": 128_000,
    "llama-3.3-70b-versatile": 128_000,
    "groq/llama-3.1-8b-instant": 128_000,
    "llama-3.1-8b-instant": 128_000,
    "groq/llama3-8b-8192": 8_192,
    "groq/mixtral-8x7b-32768": 32_768,
    "meta-llama/llama-4-scout-17b-16e-instruct": 128_000,
    "llama-4-scout-17b-16e-instruct": 128_000,
    "groq/llama-4-scout": 128_000,
    "llama-4-scout": 128_000,
    # Gemini models
    "gemini-2.5-flash": 128_000,
    "gemini-2.5-pro": 128_000,
    "gemini-1.5-flash": 128_000,
    "gemini-1.5-pro": 128_000,
    "gemini": 128_000,
}

DEFAULT_CONTEXT_LIMIT = 8_192  # Conservative default for unknown models


# ── Token counting ─────────────────────────────────────────────────────

_tiktoken_encoding = None


def _get_tiktoken():
    """Lazy-load tiktoken to avoid import cost when using Ollama."""
    global _tiktoken_encoding
    if _tiktoken_encoding is None:
        try:
            import tiktoken
            _tiktoken_encoding = tiktoken.get_encoding("cl100k_base")
        except ImportError:
            logger.warning("tiktoken_not_installed", fallback="char_estimation")
            _tiktoken_encoding = False  # Sentinel: unavailable
    return _tiktoken_encoding


def count_tokens(text: str, model: Optional[str] = None) -> int:
    """
    Count tokens in a text string.
    
    Uses tiktoken for accurate counting when available,
    falls back to character-based estimation (≈4 chars/token).
    """
    if not text:
        return 0

    enc = _get_tiktoken()
    if enc and enc is not False:
        return len(enc.encode(text))

    # Fallback: rough estimation (1 token ≈ 4 characters)
    return max(1, len(text) // 4)


def count_message_tokens(messages: List[BaseMessage], model: Optional[str] = None) -> int:
    """Count total tokens across a list of LangChain messages."""
    total = 0
    for msg in messages:
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        # Each message has ~4 tokens of overhead (role, delimiters)
        total += count_tokens(content, model) + 4
    return total


# ── Context budget ─────────────────────────────────────────────────────

class TokenBudget:
    """Allocates the context window across different components."""

    def __init__(self, model: Optional[str] = None, max_tokens: Optional[int] = None):
        self.model = model or "unknown"
        self.max_tokens = max_tokens or self._resolve_limit(self.model)

        # Fixed allocations
        self.system_prompt = 1_000
        self.tools = 1_500
        self.response_buffer = min(2_000, self.max_tokens // 4)

        # Dynamic allocations (remaining budget)
        self._remaining = self.max_tokens - self.system_prompt - self.tools - self.response_buffer
        self.workspace_context = min(2_000, self._remaining // 3)
        self.conversation = self._remaining - self.workspace_context

    def _resolve_limit(self, model: str) -> int:
        """Look up model context limit."""
        # Direct match
        if model in MODEL_CONTEXT_LIMITS:
            return MODEL_CONTEXT_LIMITS[model]

        # Partial match (e.g., "ollama/qwen2.5-coder:32b" → "qwen2.5-coder:32b")
        clean = model.split("/")[-1] if "/" in model else model
        if clean in MODEL_CONTEXT_LIMITS:
            return MODEL_CONTEXT_LIMITS[clean]

        # Substring fallback match (e.g., if model name matches key substring or vice versa)
        for key, limit in MODEL_CONTEXT_LIMITS.items():
            if key in clean or clean in key:
                return limit

        return DEFAULT_CONTEXT_LIMIT

    @property
    def available_for_conversation(self) -> int:
        return self.conversation

    @property
    def available_for_workspace(self) -> int:
        return self.workspace_context

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system_prompt": self.system_prompt,
            "tools": self.tools,
            "workspace_context": self.workspace_context,
            "conversation": self.conversation,
            "response_buffer": self.response_buffer,
        }


# ── Context Manager ────────────────────────────────────────────────────

class ContextManager:
    """
    Manages the context window for LLM calls.

    Responsibilities:
      1. Count tokens across all context components
      2. Prioritize recent messages over old ones
      3. Truncate or summarize when over budget
      4. Inject workspace summaries within budget
    """

    def __init__(self, model: Optional[str] = None, max_tokens: Optional[int] = None):
        self.budget = TokenBudget(model=model, max_tokens=max_tokens)

    def prune_messages(
        self,
        messages: List[BaseMessage],
        *,
        keep_first: int = 1,
        keep_last: int = 10,
        max_tokens: Optional[int] = None,
    ) -> List[BaseMessage]:
        """
        Prune message history to fit within the conversation budget.

        Strategy:
          1. Always keep the first `keep_first` messages (original SRS/requirements)
          2. Always keep the last `keep_last` messages (recent context)
          3. Summarize everything in between into a single system message
          4. If still over budget, progressively reduce `keep_last`
        """
        budget = max_tokens or self.budget.available_for_conversation

        if count_message_tokens(messages) <= budget:
            return messages  # Everything fits

        if len(messages) <= keep_first + keep_last:
            # Can't split further — just truncate individual messages
            return self._truncate_long_messages(messages, budget)

        # Split into sections
        first_msgs = messages[:keep_first]
        middle_msgs = messages[keep_first:-keep_last]
        last_msgs = messages[-keep_last:]

        # Summarize middle section
        summary = self._summarize_messages(middle_msgs)
        summary_msg = SystemMessage(
            content=f"[CONVERSATION SUMMARY — {len(middle_msgs)} messages compressed]\n{summary}"
        )

        pruned = first_msgs + [summary_msg] + last_msgs

        # Check if we fit now
        if count_message_tokens(pruned) <= budget:
            logger.info(
                "context_pruned",
                original=len(messages),
                pruned_to=len(pruned),
                summarized=len(middle_msgs),
            )
            return pruned

        # Still too large — reduce keep_last and retry
        if keep_last > 3:
            return self.prune_messages(
                messages,
                keep_first=keep_first,
                keep_last=keep_last - 2,
                max_tokens=budget,
            )

        # Last resort: hard truncate
        return self._truncate_long_messages(pruned, budget)

    def _summarize_messages(self, messages: List[BaseMessage]) -> str:
        """
        Create a concise summary of messages without calling the LLM.
        Extracts key actions, file operations, and decisions.
        """
        actions = []
        files_written = []
        commands_run = []
        errors = []

        for msg in messages:
            content = msg.content if isinstance(msg.content, str) else str(msg.content)

            # Extract file writes
            file_matches = re.findall(r"<write\s+path=['\"]([^'\"]+)['\"]>", content)
            files_written.extend(file_matches)

            # Extract commands
            cmd_matches = re.findall(r"<run>(.*?)</run>", content, re.DOTALL)
            commands_run.extend(cmd.strip()[:80] for cmd in cmd_matches)

            # Extract errors
            if "error" in content.lower() or "Error" in content:
                error_line = content.split("\n")[0][:120]
                errors.append(error_line)

            # Extract key decisions from AI messages
            if isinstance(msg, AIMessage) and len(content) > 50:
                first_line = content.split("\n")[0][:100]
                if not first_line.startswith("<"):
                    actions.append(first_line)

        parts = []
        if files_written:
            parts.append(f"Files created/modified: {', '.join(set(files_written))}")
        if commands_run:
            parts.append(f"Commands executed: {'; '.join(commands_run[:5])}")
        if errors:
            parts.append(f"Errors encountered: {'; '.join(errors[:3])}")
        if actions:
            parts.append(f"Key actions: {'; '.join(actions[:5])}")

        return "\n".join(parts) if parts else "General implementation progress."

    def _truncate_long_messages(
        self, messages: List[BaseMessage], budget: int
    ) -> List[BaseMessage]:
        """Truncate individual messages that are too long."""
        truncated = []
        remaining = budget

        for msg in messages:
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            tokens = count_tokens(content)

            if tokens > remaining // max(1, len(messages) - len(truncated)):
                # Truncate this message
                max_chars = (remaining // max(1, len(messages) - len(truncated))) * 4
                content = content[:max_chars] + "\n...[truncated]"

            remaining -= count_tokens(content) + 4

            if isinstance(msg, HumanMessage):
                truncated.append(HumanMessage(content=content))
            elif isinstance(msg, AIMessage):
                truncated.append(AIMessage(content=content))
            elif isinstance(msg, SystemMessage):
                truncated.append(SystemMessage(content=content))
            else:
                truncated.append(msg)

        return truncated

    def get_context_stats(self, messages: List[BaseMessage]) -> dict:
        """Return diagnostic stats about current context usage."""
        msg_tokens = count_message_tokens(messages)
        return {
            "message_count": len(messages),
            "message_tokens": msg_tokens,
            "budget": self.budget.to_dict(),
            "usage_percent": round(
                (msg_tokens / self.budget.available_for_conversation) * 100, 1
            ),
            "over_budget": msg_tokens > self.budget.available_for_conversation,
        }
