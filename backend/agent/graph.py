from contextlib import AsyncExitStack

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from .nodes import plan_node, setup_environment_node, implement_node, execute_node, validate_node
from .research_node import research_node
from .judge_node import judge_node
from .state import AgentState
from core.config import get_settings
from core.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# ── Module-level singleton ──────────────────────────────────────────────
_compiled_graph = None
_checkpointer_stack = AsyncExitStack()


def route_after_execute(state: AgentState) -> str:
    obs = state.get('last_obs')
    if obs and getattr(obs, 'exit_code', 1) == 0:
        return 'success'
    if state.get('retries', 0) >= 5:
        return 'max_retry'
    return 'error'


def route_after_validate(state: AgentState) -> str:
    obs = state.get('last_obs')
    return 'pass' if obs and getattr(obs, 'app_started', False) else 'fail'


def route_after_implement(state: AgentState) -> str:
    # If the implement node emitted <finish>, go to validate
    if state.get('status') == 'validate':
        return 'validate'
    return 'execute'


def route_after_judge(state: AgentState) -> str:
    approved = state.get('plan_approved', False)
    attempts = state.get('judge_attempts', 0)
    if approved:
        return 'implement'
    if attempts >= 3:
        logger.warning("judge_max_attempts_exceeded_proceeding", session_id=state.get('session_id', ''))
        return 'implement'
    return 'plan'


async def _create_checkpointer():
    """
    Try to create a PostgreSQL checkpointer for durable state persistence.
    Falls back to in-memory if the database is unavailable.
    """
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        checkpointer = await _checkpointer_stack.enter_async_context(
            AsyncPostgresSaver.from_conn_string(settings.database_url)
        )
        await checkpointer.setup()  # creates tables if they don't exist
        logger.info("checkpointer_init", backend="postgres")
        return checkpointer
    except Exception as e:
        logger.warning(
            "checkpointer_fallback",
            reason=str(e),
            backend="memory",
        )
        return MemorySaver()


async def close_checkpointer():
    """Close any long-lived checkpointer resources."""
    global _checkpointer_stack
    await _checkpointer_stack.aclose()
    _checkpointer_stack = AsyncExitStack()


async def build_graph(checkpointer=None):
    """Build and compile the LangGraph state machine."""
    if checkpointer is None:
        checkpointer = await _create_checkpointer()

    g = StateGraph(AgentState)

    g.add_node('plan', plan_node)
    g.add_node('research', research_node)
    g.add_node('setup_environment', setup_environment_node)
    g.add_node('judge', judge_node)
    g.add_node('implement', implement_node)
    g.add_node('execute', execute_node)
    g.add_node('validate', validate_node)

    # Flow: plan → research → setup_environment → judge → check approval
    g.set_entry_point('plan')
    g.add_edge('plan', 'research')
    g.add_edge('research', 'setup_environment')
    g.add_edge('setup_environment', 'judge')

    g.add_conditional_edges('judge', route_after_judge, {
        'plan': 'plan',
        'implement': 'implement'
    })

    g.add_conditional_edges('implement', route_after_implement, {
        'execute': 'execute',
        'validate': 'validate'
    })

    g.add_conditional_edges('execute', route_after_execute, {
        'error': 'implement',     # retry on failure
        'success': 'implement',   # go back to write more code until <finish>
        'max_retry': END,
    })

    g.add_conditional_edges('validate', route_after_validate, {
        'pass': END,
        'fail': 'implement',
    })

    # Compile the graph with checkpointer
    # Note: recursion_limit is set at invocation time, not compile time
    return g.compile(checkpointer=checkpointer)


async def get_graph():
    """Return a cached compiled graph (singleton per process)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = await build_graph()
    return _compiled_graph
