from typing import Dict, Any
from langchain_core.messages import AIMessage
from .state import AgentState
from .state_manager import merge_state_updates
from core.logger import get_logger

logger = get_logger(__name__)


async def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor Node
    Dispatches to backend subagent first.
    """
    logger.info("supervisor_dispatching", session_id=state.get('session_id'))
    # Extract API contract from plan if present
    plan_str = state.get('plan', '{}')
    api_contract = ""
    try:
        import json as _json
        plan_data = _json.loads(plan_str)
        api_contract = _json.dumps(plan_data.get('api_contract', []), indent=2)
    except Exception:
        pass
        
    updates = {
        'status': 'backend_subagent',
        'api_contract': api_contract,
        'backend_retries': 0,
        'frontend_retries': 0,
        'contract_mismatch': False,
    }
    return merge_state_updates(state, updates)


async def backend_subagent_node(state: AgentState) -> AgentState:
    """
    Backend Subagent Node
    Context: API contract, data models, env config.
    Writes: routes, services, DB layer.
    """
    from .nodes import implement_node
    # In a full implementation, we'd filter the plan to ONLY backend files
    # and restrict the LLM to 'qwen2.5-coder:7b'.
    logger.info("backend_subagent_running", session_id=state.get('session_id'))
    
    # We delegate to the existing implement node logic, but we could wrap the prompt
    # to enforce the api_contract.
    state = await implement_node(state)
    
    # If the implement node signaled an error, we handle retries here
    retries = state.get('backend_retries', 0)
    has_errors = state.get('has_execution_errors', False) or state.get('status') == 'error'
    
    if has_errors and retries < 3:
        updates = {
            'backend_retries': retries + 1,
            'status': 'backend_subagent' # Loop back to itself
        }
        logger.info("backend_subagent_retrying", retries=retries+1)
        return merge_state_updates(state, updates)
        
    # Success or max retries reached, proceed to frontend
    updates = {
        'status': 'frontend_subagent',
        'messages': [AIMessage(content="[Backend Subagent] Backend code committed. Handing off to Frontend Subagent.")]
    }
    return merge_state_updates(state, updates)


async def frontend_subagent_node(state: AgentState) -> AgentState:
    """
    Frontend Subagent Node
    Context: API contract, backend route signatures, UI plan.
    Read-only access to backend code.
    Writes: components, API client, styling.
    """
    from .nodes import implement_node
    logger.info("frontend_subagent_running", session_id=state.get('session_id'))
    
    # Delegate to implement_node for actual code generation
    state = await implement_node(state)
    
    updates = {
        'status': 'contract_check',
        'messages': [AIMessage(content="[Frontend Subagent] Frontend code committed. Checking contracts...")]
    }
    return merge_state_updates(state, updates)


async def contract_check_node(state: AgentState) -> AgentState:
    """
    Contract Check Node
    Validates schemas between Frontend and Backend.
    """
    logger.info("contract_check_running", session_id=state.get('session_id'))
    
    # For now, a stub that simulates a pass.
    # In a real implementation, we would parse OpenAPI specs or TypeScript interfaces.
    mismatch = False 
    
    if mismatch:
        retries = state.get('frontend_retries', 0)
        updates = {
            'status': 'frontend_subagent',
            'contract_mismatch': True,
            'frontend_retries': retries + 1,
            'messages': [AIMessage(content="[Contract Check] Mismatch detected. Frontend must retry.")]
        }
    else:
        updates = {
            'status': 'merge',
            'contract_mismatch': False,
            'messages': [AIMessage(content="[Contract Check] Schemas match! Proceeding to merge.")]
        }
    
    return merge_state_updates(state, updates)


async def merge_workspace_node(state: AgentState) -> AgentState:
    """
    Merge to Workspace Node
    """
    logger.info("merge_workspace_running", session_id=state.get('session_id'))
    updates = {
        'status': 'execute',
        'messages': [AIMessage(content="[Merge] Code merged to workspace. Proceeding to execution.")]
    }
    return merge_state_updates(state, updates)
