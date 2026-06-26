import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate

from agent.llm import LLMFactory
from agent.state import AgentState
from agent.architectural_artifacts import ArchitecturalPlan, ArchitecturalArtifacts
from agent.adr_manager import ADRManager
from agent.mermaid_validator import is_valid_mermaid
from agent.state_manager import merge_state_updates, log_state_transition
from core.logger import get_logger
from models.llm_profile import LLMProfile

logger = get_logger(__name__)

# Prompt for generating system architecture diagrams in JSON format
ARCH_PLANNER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a senior software architect. Your job is to design a high-level system architecture layout for the project described in the project plan.
You must generate five distinct Mermaid diagrams:
1. system_diagram: graph TB showing high-level containers/tiers (e.g. Client, Server, DB).
2. component_diagram: flowchart LR showing logical components inside the application.
3. data_flow_diagram: graph LR showing data pipelines or request-response flows.
4. sequence_diagrams: A list containing exactly 1 sequenceDiagram of a primary user interaction flow.
5. deployment_diagram: graph TB showing physical deployment nodes (e.g. Docker, Hosting, Cloud).

CRITICAL Mermaid v11.15.0 Syntax Rules:
- Diagram header must be valid (e.g., `graph TD`, `flowchart LR`, `sequenceDiagram`).
- All node IDs must be simple alphanumeric strings with NO spaces or special characters (e.g., `DatabaseNode` not `Database Node`).
- You MUST double-quote all node labels that contain spaces, parentheses, brackets, or special characters: e.g., `A["Component (details)"]` is valid, `A[Component (details)]` is INVALID.
- Do NOT use HTML tags in node labels (e.g., no `<b>` or `<br>`).
- Ensure all brackets `[]`, braces `{{}}`, parentheses `()`, and quotes `""` are balanced on each line.
- For relationships, use standard arrows like `-->`, `-.->`, or `==>`.

Format your output strictly as a JSON object, with NO markdown formatting, NO prose, and NO trailing commas:
{{
    "system_diagram": "graph TB\\n  Client[\"Web Client (Browser)\"] --> App[\"Backend App (Node.js)\"]\\n  App --> DB[\"Database (PostgreSQL)\"]",
    "component_diagram": "flowchart LR\\n  UI[\"Frontend UI\"] --> Auth[\"Auth Service\"]\\n  Auth --> UserDB[\"User Database\"]",
    "data_flow_diagram": "graph LR\\n  User[\"User Input\"] --> API[\"API Gateway\"]\\n  API --> Process[\"Data Processor\"]",
    "sequence_diagrams": ["sequenceDiagram\\n  participant U as User\\n  participant A as API\\n  U->>A: Request Data\\n  A-->>U: Return JSON"],
    "deployment_diagram": "graph TB\\n  User[\"User\"] --> CDN[\"Cloudflare CDN\"]\\n  CDN --> Server[\"Production Server\"]"
}}
"""),
    ("human", """PROJECT PLAN:
{plan}

{previous_feedback_context}

Generate the complete architectural diagrams in JSON format.""")
])


def _resolve_arch_llm(state: AgentState):
    """Use a strong planner model for architectural design."""
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
        
    return factory.create(provider=provider, model_name=model_name, role="planner")


async def architecture_plan_node(state: AgentState) -> AgentState:
    """
    LangGraph Node: Architectural Planning phase.
    Generates Mermaid diagrams and ADRs based on the bootstrap plan.
    Runs immediately after plan_bootstrap.
    """
    session_id = state.get("session_id", "")
    old_status = state.get("status", "architecture")
    
    # 1. Parse bootstrap plan
    plan_str = state.get("plan", "{}")
    try:
        plan_dict = json.loads(plan_str)
    except Exception as e:
        logger.error("arch_plan_node_parse_failed", session_id=session_id, error=str(e))
        plan_dict = {}

    tech_stack = plan_dict.get("tech_stack", {})
    tech_stack_summary = ", ".join(f"{k}: {v}" for k, v in tech_stack.items()) if tech_stack else "Standard tech stack"

    # Build retry and revision count
    revision = 1
    existing_plan = state.get("architectural_plan")
    if existing_plan:
        if hasattr(existing_plan, "architecture_revision"):
            revision = existing_plan.architecture_revision + 1
        elif isinstance(existing_plan, dict):
            revision = existing_plan.get("architecture_revision", 0) + 1

    # Get previous feedback if available
    previous_feedback_context = ""
    if existing_plan:
        if hasattr(existing_plan, "architecture_feedback"):
            feedback = getattr(existing_plan, "architecture_feedback", "")
        elif isinstance(existing_plan, dict):
            feedback = existing_plan.get("architecture_feedback", "")
        else:
            feedback = ""
            
        if feedback:
            previous_feedback_context = f"PREVIOUS GENERATION FEEDBACK (Please resolve these errors):\n{feedback}\n"

    logger.info(
        "arch_plan_node_start",
        session_id=session_id,
        revision=revision,
        tech_stack=tech_stack
    )

    try:
        # 2. Invoke LLM to generate diagrams
        llm = _resolve_arch_llm(state)
        chain = ARCH_PLANNER_PROMPT | llm
        
        response = await chain.ainvoke({
            "plan": plan_str,
            "previous_feedback_context": previous_feedback_context
        })

        raw_text = response.content
        from agent.nodes import extract_plan_json
        json_str = extract_plan_json(raw_text)
        artifacts = ArchitecturalArtifacts.model_validate_json(json_str)

        # 3. Create ADRs
        adrs = [
            ADRManager.generate_tech_stack_adr(tech_stack),
            ADRManager.generate_deployment_adr(plan_dict),
            ADRManager.generate_data_persistence_adr(plan_dict)
        ]

        # 4. Construct complete ArchitecturalPlan
        arch_plan = ArchitecturalPlan(
            architecture_generated_at=datetime.utcnow().isoformat() + "Z",
            architectural_artifacts=artifacts,
            architecture_decisions=adrs,
            architecture_approved=True,
            architecture_revision=revision,
            architecture_feedback="",
            tech_stack_summary=tech_stack_summary,
            estimated_complexity="Medium"
        )

        # Update State
        updates = {
            "architectural_plan": arch_plan,
            "architecture_phase": "Complete",
            "status": "research",  # Node transition state
            "judge_attempts": 0,   # Reset judge attempts upon new architecture
            "messages": [AIMessage(content=f"[Architecture Plan Complete] Generated 5 diagrams & 3 ADRs for tech stack: {tech_stack_summary}.")]
        }

        new_state = merge_state_updates(state, updates)
        log_state_transition(session_id, old_status, "research", {"reason": "architecture_complete"})
        return new_state

    except Exception as e:
        logger.error("arch_plan_node_failed", session_id=session_id, error=str(e))
        
        # Mark as Rejected with error details
        rejected_plan = ArchitecturalPlan(
            architecture_generated_at=datetime.utcnow().isoformat() + "Z",
            # Fallback empty artifacts to allow compilation
            architectural_artifacts=ArchitecturalArtifacts(
                system_diagram="graph TD\n    A[Error] --> B[Failed]",
                component_diagram="graph TD\n    A[Error] --> B[Failed]",
                data_flow_diagram="graph TD\n    A[Error] --> B[Failed]",
                sequence_diagrams=["sequenceDiagram\n    A->>B: Error"],
                deployment_diagram="graph TD\n    A[Error] --> B[Failed]"
            ),
            architecture_decisions=[],
            architecture_approved=False,
            architecture_revision=revision,
            architecture_feedback=f"Architecture generation failed: {str(e)}",
            tech_stack_summary=tech_stack_summary,
            estimated_complexity="Medium"
        )

        updates = {
            "architectural_plan": rejected_plan,
            "architecture_phase": "Rejected",
            "status": "architecture",  # Remain in architecture state for retry
            "messages": [AIMessage(content=f"[Architecture Plan Failed] Reason: {str(e)}")]
        }
        
        new_state = merge_state_updates(state, updates)
        log_state_transition(session_id, old_status, "architecture", {"reason": "generation_failed", "error": str(e)})
        return new_state
