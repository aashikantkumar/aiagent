"""
Research Node — the "brain" that learns HOW to code before coding begins.

This LangGraph node sits between PLAN and SETUP_ENVIRONMENT. It:
  1. Reads the project plan (tech stack, file list)
  2. Generates targeted web search queries
  3. Fetches real-time documentation and tutorials
  4. Synthesizes everything into a compact "coding guide"
  5. Passes the guide to the implement node via state

The result: the agent knows the EXACT scaffolding commands, project
structure, dependency versions, and best practices — not just what
its training data remembers.
"""
import json as _json
import asyncio

from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate

from .web_search import search_and_extract, generate_research_queries, search_web
from .llm import LLMFactory
from .state import AgentState
from core.logger import get_logger
from models.llm_profile import LLMProfile

logger = get_logger(__name__)



# ── Research synthesis prompt ──────────────────────────────────────────────

RESEARCH_SYNTHESIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a senior software architect. You've just searched the web
for the latest documentation on how to build a project. Your job is to
synthesize the search results into a CONCISE, ACTIONABLE coding guide.

CRITICAL: The coding guide MUST strictly align with the tech stack specified in the PROJECT PLAN.
- If the project plan specifies "html_css_js" or Vanilla JavaScript (no framework), DO NOT suggest React, Vue, TypeScript, or Vite. Provide instructions for a vanilla HTML/CSS/JS setup using a simple web server (e.g. `python3 -m http.server 3000`).
- If the project plan specifies a specific framework (React, Express, FastAPI, etc.), provide the exact scaffolding and dependencies for THAT stack.

Focus ONLY on:
1. EXACT scaffolding commands (if applicable)
2. Correct project file structure
3. Latest package versions and important dependencies
4. Configuration gotchas
5. Dev server startup command and expected port

DO NOT include:
- General explanations of what React/Vue/etc. is
- Marketing language
- Deployment instructions
- Testing setup (unless asked)

Format your output as a structured reference sheet, not prose."""),

    ("human", """PROJECT PLAN:
{plan}

WEB SEARCH RESULTS:
{search_results}

Synthesize these into a compact coding guide. Include EXACT commands and file paths."""),
])


def _resolve_research_llm(state: AgentState):
    """Use a fast, cheap model for research synthesis."""
    factory = LLMFactory()
    profile_data = state.get("llm_profile")
    
    provider = None
    model_name = None
    if isinstance(profile_data, LLMProfile):
        provider = profile_data.provider
        model_name = profile_data.model
    elif isinstance(profile_data, dict):
        provider = profile_data.get("provider")
        model_name = profile_data.get("model")
        
    return factory.create(provider=provider, model_name=model_name, role="validator")  # Fast model for summarization


async def research_node(state: AgentState) -> AgentState:
    """
    LangGraph node: Research how to build the project.

    Reads the plan, searches the web for latest docs, and produces
    a structured coding guide for the implement node.
    """
    session_id = state.get("session_id", "")
    plan_str = state.get("plan", "{}")

    # Parse the plan
    try:
        plan = _json.loads(plan_str)
    except _json.JSONDecodeError:
        logger.warning("research_plan_parse_failed", session_id=session_id)
        plan = {}

    # ── Step 1: Generate search queries ────────────────────────────────
    queries = generate_research_queries(plan)

    if not queries:
        logger.info("research_no_queries", session_id=session_id)
        return {
            "research_context": "No specific tech stack detected. Using general best practices.",
            "status": "setup_env",
            "messages": [AIMessage(content="[Research] No specific framework detected — using general practices.")],
        }

    logger.info(
        "research_start",
        session_id=session_id,
        num_queries=len(queries),
        queries=queries,
    )

    # ── Step 2: Execute web searches ───────────────────────────────────
    all_results = []
    for query in queries:
        try:
            response = await search_and_extract(
                query=query,
                max_results=3,
                max_content_chars=3000,
                fetch_content=True,
            )

            if response.error:
                logger.warning(
                    "research_search_error",
                    session_id=session_id,
                    query=query,
                    error=response.error,
                )
                # Fallback: try without content extraction
                response = await search_web(query, max_results=3)

            for result in response.results:
                all_results.append({
                    "query": query,
                    "title": result.title,
                    "url": result.url,
                    "snippet": result.snippet,
                    "content": result.content[:2000] if result.content else "",
                })

        except Exception as e:
            logger.error(
                "research_query_failed",
                session_id=session_id,
                query=query,
                error=str(e),
            )

    if not all_results:
        logger.warning("research_no_results", session_id=session_id)
        return {
            "research_context": "Web search returned no results. Using LLM training knowledge.",
            "status": "setup_env",
            "messages": [AIMessage(content="[Research] Web search unavailable — using training knowledge.")],
        }

    # ── Step 3: Format search results for LLM ─────────────────────────
    formatted_results = []
    for i, r in enumerate(all_results, 1):
        entry = f"### Result {i}: {r['title']}\n"
        entry += f"URL: {r['url']}\n"
        entry += f"Query: {r['query']}\n"
        entry += f"Snippet: {r['snippet']}\n"
        if r["content"]:
            entry += f"Page Content:\n{r['content'][:1500]}\n"
        formatted_results.append(entry)

    search_text = "\n---\n".join(formatted_results)

    # Truncate to avoid context overflow
    if len(search_text) > 12000:
        search_text = search_text[:12000] + "\n\n... [additional results truncated]"

    # ── Step 4: Synthesize with LLM ────────────────────────────────────
    try:
        llm = _resolve_research_llm(state)
        chain = RESEARCH_SYNTHESIS_PROMPT | llm

        # Small delay for rate limiting
        await asyncio.sleep(0.5)

        response = await chain.ainvoke({
            "plan": plan_str,
            "search_results": search_text,
        })

        research_context = response.content if isinstance(response.content, str) else str(response.content)

        logger.info(
            "research_complete",
            session_id=session_id,
            context_length=len(research_context),
            num_results=len(all_results),
        )

    except Exception as e:
        # If LLM synthesis fails, use raw search results as fallback
        logger.error("research_synthesis_failed", session_id=session_id, error=str(e))
        research_context = f"Raw search findings:\n\n"
        for r in all_results[:5]:
            research_context += f"- {r['title']}: {r['snippet']}\n"

    return {
        "research_context": research_context,
        "status": "setup_env",
        "messages": [AIMessage(content=f"[Research Complete]\n{research_context}")],
    }


async def search_for_error(error_message: str, tech_context: str = "") -> str:
    """
    Mini-research function: search the web for how to fix a specific error.

    Called from the implement node when it encounters an unknown error
    and emits a <search> action.

    Args:
        error_message: The error message to research
        tech_context: Optional tech stack context (e.g., "react vite typescript")

    Returns:
        Compact fix instructions as a string
    """
    # Clean up the error message for a better search query
    clean_error = error_message.strip()
    # Remove file paths and line numbers for a more generic search
    clean_error = clean_error.split("\n")[0][:150]

    query = f"{tech_context} fix error: {clean_error}".strip()

    try:
        response = await search_and_extract(
            query=query,
            max_results=3,
            max_content_chars=2000,
            fetch_content=True,
        )

        if not response.results:
            return f"No search results found for: {clean_error}"

        # Build a compact fix guide from results
        fix_guide = f"Web search results for error: {clean_error}\n\n"
        for r in response.results:
            fix_guide += f"**{r.title}** ({r.url})\n"
            fix_guide += f"{r.snippet}\n"
            if r.content:
                # Extract just the most relevant part
                fix_guide += f"Details: {r.content[:500]}\n"
            fix_guide += "\n"

        return fix_guide[:3000]

    except Exception as e:
        logger.error("search_for_error_failed", error=str(e))
        return f"Error search failed: {e}"
