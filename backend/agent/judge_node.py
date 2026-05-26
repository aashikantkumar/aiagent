"""
Judge Node — Evaluates the plan, environment setup, and web research
against user requirements before any coding happens.

If the plan has gaps, missing files, or incompatible versions/commands
relative to the environment, the Judge rejects it with a critique.
The graph then loops back to PLAN to refine the strategy.
"""
import json as _json
import re
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from .llm import LLMFactory
from .state import AgentState
from core.logger import get_logger
from models.llm_profile import LLMProfile

logger = get_logger(__name__)


# ── Judge Prompt ────────────────────────────────────────────────────────────

JUDGE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a senior software quality control engineer and code auditor.
Your job is to inspect the project plan, environment setup, and web research findings
to determine if the plan is sound, executable, and complete BEFORE the developers start coding.

Evaluate the plan against these criteria:
1. COMPLETENESS: Does the plan list all files necessary to build the complete, functional application as described in the requirements (SRS)?
2. SCAFFOLDING & COMPATIBILITY: Are the scaffolding/run commands realistic and correct for the detected environment? (e.g. if React/Vite is used, is there npm/node? is Vite configured properly?)
3. STEP-BY-STEP FEASIBILITY: Is the order of execution logical? Is there anything missing (like config files, packages, databases connection code)?
4. DOCKER FRIENDLINESS: Do server start commands run in the background (using '&')? Are hosts configured correctly (e.g., binding to '0.0.0.0' or 'localhost') so ports are accessible?

Output your evaluation in EXACTLY this JSON structure (no markdown outside the JSON block):
{{
  "approved": true or false,
  "score": 1 to 10,
  "critique": "Detailed list of issues, gaps, or changes required. Be specific about missing files, wrong commands, or config improvements. If approved, list key recommendations."
}}"""),

    ("human", """REQUIREMENTS (SRS):
{srs_text}

PROPOSED PROJECT PLAN:
{plan}

SANDBOX ENVIRONMENT SETUP:
{environment_info}

WEB RESEARCH FINDINGS:
{research_context}

Perform your evaluation and output the JSON evaluation block now."""),
])


def _resolve_judge_llm(state: AgentState):
    """Use a high-reasoning model (planner role) to act as the Judge."""
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


def extract_judge_json(content: str) -> dict:
    """Extracts JSON block from the LLM's response."""
    fenced = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', content)
    if fenced:
        content = fenced.group(1)

    start = content.find('{')
    if start >= 0:
        depth = 0
        for idx, char in enumerate(content[start:], start=start):
            if char == '{':
                depth += 1
            elif char == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return _json.loads(content[start:idx + 1].strip())
                    except _json.JSONDecodeError:
                        break

    # Fallback parsing if JSON decode fails
    return {
        "approved": "true" in content.lower() and "false" not in content.lower(),
        "score": 5,
        "critique": f"Could not parse structured critique. Raw response: {content}"
    }


async def judge_node(state: AgentState) -> AgentState:
    """
    LangGraph node: Evaluate the plan before implementing it.

    Compares plan + research + environment info against requirements.
    Updates approval status and feedback.
    """
    session_id = state.get("session_id", "")
    srs = state.get("messages", [None])[0].content if state.get("messages") else ""
    plan = state.get("plan", "{}")
    env_info = state.get("environment_info", "No environment info")
    research_ctx = state.get("research_context", "No research context")
    attempts = state.get("judge_attempts", 0)

    logger.info("judge_start", session_id=session_id, attempt=attempts + 1)

    try:
        llm = _resolve_judge_llm(state)
        chain = JUDGE_PROMPT | llm

        response = await chain.ainvoke({
            "srs_text": srs,
            "plan": plan,
            "environment_info": env_info,
            "research_context": research_ctx,
        })

        content = response.content if isinstance(response.content, str) else str(response.content)
        result = extract_judge_json(content)

        approved = result.get("approved", False)
        critique = result.get("critique", "No critique provided.")
        score = result.get("score", 5)

        logger.info(
            "judge_complete",
            session_id=session_id,
            approved=approved,
            score=score,
            critique_len=len(critique),
        )

        return {
            "plan_approved": approved,
            "judge_feedback": critique,
            "judge_attempts": attempts + 1,
            "status": "implement" if approved else "plan",
            "messages": [AIMessage(content=f"[Judge Evaluation] Approved: {approved} (Score: {score}/10)\n\nCritique/Feedback:\n{critique}")],
        }

    except Exception as e:
        logger.error("judge_failed", session_id=session_id, error=str(e))
        # Fallback: auto-approve on error to avoid blocking execution
        return {
            "plan_approved": True,
            "judge_feedback": f"Judge node error occurred: {str(e)}. Proceeding by default.",
            "judge_attempts": attempts + 1,
            "status": "implement",
            "messages": [AIMessage(content="[Judge Warning] Judge node hit an exception, plan auto-approved by default.")],
        }
