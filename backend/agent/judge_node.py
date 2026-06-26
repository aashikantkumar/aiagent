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
from .context_manager import ContextManager, count_tokens
from core.logger import get_logger
from models.llm_profile import LLMProfile

logger = get_logger(__name__)


# ── Judge Prompt ────────────────────────────────────────────────────────────

JUDGE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a senior plan reviewer. Evaluate the project plan against user requirements using these criteria:

**CRITERIA** (score each 1-10):
1. COMPLETENESS: Does the plan list ALL files needed? Every UI component, route, config, and data model?
   (Rubric: 10=Every file present, 5=Missing minor files, 1=Missing core files)
2. COMPATIBILITY: Are scaffolding/run commands correct for the detected environment? Version-correct?
   (Rubric: 10=Perfect match, 5=Minor version mismatch, 1=Wrong environment)
3. FEASIBILITY: Is the execution order logical? Are dependencies installed before imports?
   (Rubric: 10=Logical order, 5=Some order issues, 1=Circular or broken order)
4. DOCKER/SERVER: Do server commands run in the background (using '&')? Are hosts binding to '0.0.0.0'?
   (If tech_stack.backend = 'none': score this 10/10 automatically. Rubric: 10=Perfect/NA, 5=Missing &, 1=Binds to localhost)
5. FILE_COVERAGE: For each requirement in the SRS, is there at least one file in the plan that addresses it?
   (Rubric: 10=All requirements covered, 5=Partial coverage, 1=Major missing features)

**CHECKLIST** (answer YES or NO for each):
- [ ] All user-facing features have corresponding files
- [ ] package.json / requirements.txt lists all needed dependencies (If tech_stack.backend = 'none' and no framework, confirm no npm dependencies needed)
- [ ] Dev server start command is correct and runs in background
- [ ] Server binds to 0.0.0.0 (not localhost/127.0.0.1) (Answer YES if no server is needed)
- [ ] No circular dependency in task execution order

Output EXACTLY this JSON (no markdown outside):
{{
  "approved": true or false,
  "score": 1 to 10,
  "criteria_scores": {{
    "completeness": 1-10,
    "compatibility": 1-10,
    "feasibility": 1-10,
    "docker": 1-10,
    "file_coverage": 1-10
  }},
  "checklist_failures": ["list of failed checklist items, if any"],
  "critique": "Specific issues or recommendations. Be concise.",
  "root_cause_analysis": "Identify why any inconsistencies occurred (e.g. why React was generated for vanilla JS)",
  "agent_responsible": "planner or researcher"
}}"""),

    ("human", """REQUIREMENTS:
{srs_text}

PROPOSED PLAN:
{plan}

SANDBOX ENVIRONMENT:
{environment_info}

{structural_issues}

Evaluate now."""),
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
        
    # Use the fast validator model — plan review is classification, not generation
    return factory.create(provider=provider, model_name=model_name, role="validator", temperature=0.0)


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
        "criteria_scores": {},
        "checklist_failures": [],
        "critique": f"Could not parse structured critique. Raw response: {content}",
        "root_cause_analysis": "JSON Parse Failure",
        "agent_responsible": "judge"
    }


def structural_plan_check(plan_str: str, tech_stack_override: dict = None) -> dict:
    """
    Pre-LLM structural validation of the plan JSON.
    
    Catches obvious issues without burning LLM tokens:
      - Empty or unparseable plan
      - Missing files list
      - Tasks with no description or files
      - Docker binding to localhost instead of 0.0.0.0
      - Server commands missing background operator (&)
    
    Returns:
        dict with 'issues' (list of strings) and 'auto_reject' (bool)
    """
    issues = []
    auto_reject = False
    
    try:
        plan = _json.loads(plan_str)
    except (_json.JSONDecodeError, TypeError):
        return {'issues': ['Plan JSON is unparseable'], 'auto_reject': True}
    
    if not plan:
        return {'issues': ['Plan is empty'], 'auto_reject': True}
    
    # Extract tasks/steps
    tasks = plan.get('tasks', plan.get('steps', []))
    if not tasks:
        issues.append('Plan has no tasks or steps — the execution graph will be empty')
    else:
        for i, task in enumerate(tasks):
            if isinstance(task, dict):
                desc = task.get('description', task.get('content', ''))
                if not desc or len(desc) < 5:
                    issues.append(f'Task {i+1} has no meaningful description or content')
                
                # Support old 'files' array and new 'file_path' / 'file' string
                task_files = task.get('files', [])
                if not task_files:
                    f = task.get('file_path', task.get('file', ''))
                    if f:
                        task_files.append(f)
                
                if not task_files and not task.get('command') and not task.get('action'):
                    issues.append(f'Task {i+1} has no files, command, or action associated')

    # Extract all files
    files = plan.get('files', [])
    if not files:
        for t in tasks:
            if isinstance(t, dict):
                f = t.get('file_path', t.get('file', ''))
                if f:
                    files.append(f)
                for tf in t.get('files', []):
                    files.append(tf)

    if not files and tasks:
        issues.append('Plan has no files list — the agent won\'t know what to create')
    
    # Check for Docker binding issues
    plan_text = plan_str.lower()
    if 'localhost' in plan_text and '0.0.0.0' not in plan_text:
        issues.append(
            'Plan references localhost but not 0.0.0.0 — '
            'servers inside Docker MUST bind to 0.0.0.0'
        )
    
    # Check for background server commands
    commands = []
    # Check top-level run_command
    run_cmd = plan.get('run_command', '')
    if run_cmd:
        commands.append(run_cmd)
        
    for task in tasks:
        if isinstance(task, dict):
            cmd = task.get('command', '') or ''
            if cmd:
                commands.append(cmd)
    
    server_keywords = ['npm start', 'npm run dev', 'node server', 'python -m',
                       'uvicorn', 'gunicorn', 'flask run', 'python app',
                       'python main', 'python manage.py runserver']
    for cmd in commands:
        cmd_lower = cmd.lower()
        for kw in server_keywords:
            if kw in cmd_lower and '&' not in cmd and 'nohup' not in cmd_lower:
                issues.append(
                    f'Server command "{cmd[:60]}" does not run in background '
                    '(missing "&" or "nohup")'
                )
                break
    
    # Check tech_stack sanity
    tech = tech_stack_override if tech_stack_override else plan.get('tech_stack', {})
    if isinstance(tech, dict):
        frontend = tech.get('frontend', '').lower()
        backend = tech.get('backend', '').lower()
        language = tech.get('language', '').lower()
        
        # Detect contradictions and framework mismatches
        if frontend in ('react', 'vue', 'angular', 'svelte') and language == 'python':
            issues.append(
                f'Tech stack contradiction: frontend is {frontend} '
                f'but language is {language}. Frontend needs JavaScript/TypeScript.'
            )
            
        # Detect React/backend hallucination in Vanilla JS project
        if frontend == 'html_css_js' or frontend == 'none':
            for f in files:
                if isinstance(f, str) and (
                    'package.json' in f or 'vite.config' in f or 
                    'src/components' in f or '.jsx' in f or '.tsx' in f
                ):
                    issues.append(f'Framework mismatch: Vanilla JS project cannot contain {f}')
                    auto_reject = True
                    
        # Enforce architecture lock: If backend is 'none', prohibit API generation
        if backend == 'none':
            api_contract = plan.get('api_contract', [])
            if api_contract:
                issues.append('Architecture lock violation: API contract generated but backend is set to "none"')
                auto_reject = True
            for f in files:
                if isinstance(f, str) and ('server' in f or 'routes' in f or 'controllers' in f or 'models' in f):
                    issues.append(f'Architecture lock violation: Backend file {f} generated but backend is set to "none"')
                    auto_reject = True
    
    return {
        'issues': issues,
        'auto_reject': auto_reject,
    }


async def judge_node(state: AgentState) -> AgentState:
    """
    LangGraph node: Evaluate the plan before implementing it.

    Compares plan + research + environment info against requirements.
    Updates approval status and feedback.
    
    Phase 1.1 Updates:
    - Uses state_manager for safe state updates
    - Tracks judge_attempts properly
    - Logs state transitions
    - Token management integration (Task 1.3)
    """
    from .state_manager import merge_state_updates, log_state_transition
    
    old_status = state.get('status', 'judge')
    session_id = state.get("session_id", "")
    
    # ── Token Management Initialization ─────────────────────────────────
    # llm_profile may be an LLMProfile object OR a dict — pydantic models
    # have no .get(), so the isinstance check MUST come first.
    profile_data = state.get('llm_profile')
    if isinstance(profile_data, LLMProfile):
        model_name = profile_data.model or 'unknown'
    elif isinstance(profile_data, dict):
        model_name = profile_data.get('model', 'unknown')
    else:
        model_name = 'unknown'

    ctx_manager = ContextManager(model=model_name)

    if state.get('chat_mode') == 'discuss':
        updates = {
            "plan_approved": True,
            "judge_attempts": state.get("judge_attempts", 0),
            "status": "implement",
            "messages": [],
            "token_count": 0,
            "context_budget": ctx_manager.budget.to_dict(),
            # Metrics: no tokens processed in discuss mode
            "total_tokens_processed": state.get('total_tokens_processed', 0),
            "max_token_count_reached": state.get('max_token_count_reached', 0),
        }
        new_state = merge_state_updates(state, updates)
        log_state_transition(session_id, old_status, 'implement', {'reason': 'discuss_mode'})
        return new_state

    session_id = state.get("session_id", "")
    messages = state.get("messages") or []
    first_msg = messages[0] if messages else None
    if first_msg is not None:
        if hasattr(first_msg, "content"):
            srs = first_msg.content
        elif isinstance(first_msg, dict):
            srs = first_msg.get("content", "")
        else:
            srs = str(first_msg)
    else:
        srs = ""
    plan = state.get("plan", "{}")
    env_info = state.get("environment_info", "No environment info")
    research_ctx = state.get("research_context", "No research context")
    attempts = state.get("judge_attempts", 0)

    # ── Token Management: Count tokens in SRS and plan ─────────────────
    srs_tokens = count_tokens(srs, model_name)
    plan_tokens = count_tokens(plan, model_name)
    total_tokens = srs_tokens + plan_tokens
    
    # If combined tokens exceed conversation budget, truncate SRS to half of budget
    budget = ctx_manager.budget.available_for_conversation
    if total_tokens > budget:
        # Allocate half budget to SRS, half to plan
        max_srs_chars = (budget // 2) * 4  # ~4 chars per token
        original_srs_tokens = srs_tokens
        srs = srs[:max_srs_chars]
        srs_tokens = count_tokens(srs, model_name)
        logger.warning(
            "judge_srs_truncated",
            session_id=session_id,
            original_tokens=original_srs_tokens,
            truncated_tokens=srs_tokens,
            budget=budget // 2,
        )

    logger.info("judge_start", session_id=session_id, attempt=attempts + 1)

    # Attempt to extract tech_stack from state if available
    tech_stack_override = state.get("tech_stack", None)
    
    if not tech_stack_override:
        # Fallback to architecture plan
        arch_plan = state.get("architecture_plan", {})
        if isinstance(arch_plan, str):
            try:
                arch_plan = _json.loads(arch_plan)
            except:
                arch_plan = {}
        tech_stack_override = arch_plan.get("tech_stack", None)
        
    if not tech_stack_override:
        # Fallback to parsing the current plan
        try:
            parsed_plan = _json.loads(plan)
            tech_stack_override = parsed_plan.get("tech_stack", None)
        except:
            pass

    # ── Issue #4: Structural pre-validation (no LLM cost) ──────────────
    structural = structural_plan_check(plan, tech_stack_override=tech_stack_override)
    structural_issues_text = ""
    
    if structural['auto_reject']:
        # Plan is structurally broken — reject without calling LLM
        critique = "Plan auto-rejected by structural validation:\n" + "\n".join(
            f"- {issue}" for issue in structural['issues']
        )
        logger.warning(
            "judge_structural_reject",
            session_id=session_id,
            issues=structural['issues'],
        )
        
        updates = {
            "plan_approved": False,
            "judge_feedback": critique,
            "judge_attempts": attempts + 1,
            "status": "plan",
            "messages": [AIMessage(content=f"[Judge Evaluation] Approved: False (Structural Issues)\n\n{critique}")],
            "token_count": 0,
            "context_budget": ctx_manager.budget.to_dict(),
            "total_tokens_processed": state.get('total_tokens_processed', 0),
            "max_token_count_reached": state.get('max_token_count_reached', 0),
        }
        new_state = merge_state_updates(state, updates)
        log_state_transition(session_id, old_status, 'plan', {
            'auto_reject': True,
            'issues': structural['issues'],
            'attempt': attempts + 1,
        })
        return new_state
    
    if structural['issues']:
        structural_issues_text = (
            "STRUCTURAL ISSUES DETECTED (address these in your evaluation):\n"
            + "\n".join(f"- {issue}" for issue in structural['issues'])
        )

    try:
        llm = _resolve_judge_llm(state)
        chain = JUDGE_PROMPT | llm

        from agent.observability import ObservabilityCallbackHandler
        handler = ObservabilityCallbackHandler(session_id, "Judge Agent")

        response = await chain.ainvoke({
            "srs_text": srs,
            "plan": plan,
            "environment_info": env_info,
            "structural_issues": structural_issues_text,
        }, config={"callbacks": [handler]})

        content = response.content if isinstance(response.content, str) else str(response.content)
        result = extract_judge_json(content)

        approved = result.get("approved", False)
        critique = result.get("critique", "No critique provided.")
        score = result.get("score", 5)
        criteria_scores = result.get("criteria_scores", {})
        checklist_failures = result.get("checklist_failures", [])
        root_cause = result.get("root_cause_analysis", "")
        agent_responsible = result.get("agent_responsible", "")

        # Append structural issues to critique if any
        if structural['issues']:
            critique += "\n\nStructural issues found by pre-check:\n" + "\n".join(
                f"- {issue}" for issue in structural['issues']
            )

        if root_cause:
            critique += f"\n\n[Root Cause Analysis]: {root_cause} (Agent: {agent_responsible})"

        # STRICT ENFORCEMENT: Reject if score < 6
        if score < 6:
            approved = False
            critique += f"\n[Rejected: Score {score} is below threshold 6. Execution blocked.]"
            logger.warning("judge_rejected_low_score", session_id=session_id, score=score)

        # Auto-reject if any criterion is critically low (< 3)
        if criteria_scores:
            critical_failures = [
                (k, v) for k, v in criteria_scores.items()
                if isinstance(v, (int, float)) and v < 3
            ]
            if critical_failures and approved:
                approved = False
                failure_detail = ", ".join(f"{k}={v}" for k, v in critical_failures)
                critique += f"\n[Auto-rejected: Critical failures in {failure_detail}]"
                logger.warning(
                    "judge_auto_rejected_critical",
                    session_id=session_id,
                    failures=failure_detail,
                )

        logger.info(
            "judge_complete",
            session_id=session_id,
            approved=approved,
            score=score,
            criteria_scores=criteria_scores,
            critique_len=len(critique),
        )

        new_status = "implement" if approved else "plan"
        
        # ── Task 3.3: Track token metrics ──────────────────────────────
        # Calculate final token count (tokens from SRS + plan)
        final_token_count = count_tokens(srs, model_name) + plan_tokens
        
        updates = {
            "plan_approved": approved,
            "judge_feedback": critique,
            "judge_attempts": attempts + 1,
            "judge_score": score,
            "rejection_reason": critique if not approved else "",
            "architecture_feedback": critique if (not approved and attempts >= 2) else state.get("architecture_feedback", ""),
            "status": new_status,
            "messages": [AIMessage(content=f"[Judge Evaluation] Approved: {approved} (Score: {score}/10)\n\nCriteria: {_json.dumps(criteria_scores)}\nChecklist Failures: {checklist_failures}\n\nCritique/Feedback:\n{critique}")],
            "token_count": final_token_count,
            "context_budget": ctx_manager.budget.to_dict(),
            # Metrics tracking (Requirements 5.1, 5.4, 5.5)
            "total_tokens_processed": state.get('total_tokens_processed', 0) + final_token_count,
            "max_token_count_reached": max(
                state.get('max_token_count_reached', 0),
                final_token_count
            ),
        }
        
        new_state = merge_state_updates(state, updates)
        log_state_transition(session_id, old_status, new_status, {
            'approved': approved,
            'score': score,
            'criteria_scores': criteria_scores,
            'attempt': attempts + 1,
            'tokens': final_token_count,
        })
        return new_state

    except Exception as e:
        logger.error("judge_failed", session_id=session_id, error=str(e))
        # Fallback: DO NOT auto-approve on error to avoid executing invalid plans
        
        # ── Task 3.3: Track token metrics even on error ────────────────
        # Calculate token count for fallback
        fallback_token_count = count_tokens(srs, model_name) + plan_tokens
        
        updates = {
            "plan_approved": False,
            "judge_feedback": f"Judge node error occurred: {str(e)}. Execution blocked.",
            "judge_attempts": attempts + 1,
            "status": "plan",
            "messages": [AIMessage(content=f"[Judge Warning] Judge node hit an exception: {str(e)}. Execution blocked.")],
            "plan_error": str(e)[:200],
            "token_count": fallback_token_count,
            "context_budget": ctx_manager.budget.to_dict(),
            # Metrics tracking
            "total_tokens_processed": state.get('total_tokens_processed', 0) + fallback_token_count,
            "max_token_count_reached": max(
                state.get('max_token_count_reached', 0),
                fallback_token_count
            ),
        }
        new_state = merge_state_updates(state, updates)
        log_state_transition(session_id, old_status, 'implement', {
            'error': str(e)[:100],
            'tokens': fallback_token_count,
        })
        return new_state
