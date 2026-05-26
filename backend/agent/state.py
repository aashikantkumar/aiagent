from typing import TypedDict, Literal, Annotated, Dict, Any, Optional, NotRequired, List
from langgraph.graph import add_messages
from langchain_core.messages import BaseMessage
from .schema import ActionType, ObservationType
from models.llm_profile import LLMProfile


class AgentState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]   # full chat history
    status: Literal['plan', 'research', 'setup_env', 'judge', 'implement', 'execute', 'validate', 'done', 'error']
    plan: str                              # project plan JSON
    files: Dict[str, str]                  # path -> content
    last_obs: Optional[ObservationType]    # last Docker observation
    retries: int                           # retry counter
    session_id: str
    llm_profile: Optional[LLMProfile]
    _action: Optional[ActionType]          # parsed XML action passed to execute

    # ── Phase 1: Token & Context Management ──────────────────────────
    token_count: int                       # current total token usage
    context_budget: Dict[str, int]         # token budget allocation

    # ── Phase 2: Error Intelligence ──────────────────────────────────
    error_history: List[Dict[str, Any]]    # structured error analysis history
    last_error_analysis: Optional[str]     # formatted error analysis for prompt

    # ── Phase 3: Workspace Awareness ─────────────────────────────────
    workspace_summary: str                 # compact workspace context for LLM

    # ── Phase 4: Environment Setup ───────────────────────────────────
    environment_info: str                  # detected runtime/tools info for LLM

    # ── Phase 5: Web Research ────────────────────────────────────────
    research_context: str                  # synthesized web research (scaffolding, versions, structure)

    # ── Phase 6: Plan Judging ────────────────────────────────────────
    judge_feedback: str                    # feedback or critique from the judge
    plan_approved: bool                    # whether the judge approved the plan
    judge_attempts: int                    # counter for plan revision loops

