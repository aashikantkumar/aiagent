"""
Agent graph nodes — plan, implement, execute, validate.

Integrates:
  - Context Manager (Phase 1): token counting and message pruning
  - Error Analyzer (Phase 2): intelligent error classification and suggestions
  - Workspace Indexer (Phase 3): project structure awareness
  - Memory Manager (Phase 1): long-term memory compression
"""
import re
import asyncio
from langchain_core.messages import HumanMessage, AIMessage
from .llm import LLMFactory
from .prompts import plan_prompt, implement_prompt
from .state import AgentState
from runtime import DockerRuntime
from .schema import (
    CmdRunAction, FileWriteAction, FinishAction, BrowserAction, WebSearchAction,
    UnknownAction, ActionType, CmdOutputObservation, BrowserObservation,
    ErrorObservation, ValidatedObservation,
)
from .context_manager import ContextManager, count_message_tokens
from .error_analyzer import ErrorAnalyzer
from .workspace_indexer import WorkspaceIndexer
from .memory import MemoryManager
from core.config import get_settings
from core.logger import get_logger
from models.llm_profile import LLMProfile

settings = get_settings()
logger = get_logger(__name__)

# ── Module-level singletons ────────────────────────────────────────────

_error_analyzer = ErrorAnalyzer()
_memory_managers: dict[str, MemoryManager] = {}


def _get_memory_manager(session_id: str) -> MemoryManager:
    """Get or create a MemoryManager for a session."""
    if session_id not in _memory_managers:
        _memory_managers[session_id] = MemoryManager()
    return _memory_managers[session_id]


def _resolve_llm(state: AgentState, role: str | None = None):
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
        
    return factory.create(provider=provider, model_name=model_name, role=role)


def _get_model_name(state: AgentState) -> str:
    """Extract the model name from state for context management."""
    profile_data = state.get("llm_profile")
    if isinstance(profile_data, LLMProfile):
        return profile_data.model or ""
    if isinstance(profile_data, dict):
        return profile_data.get("model", "")
    return settings.DEFAULT_LLM_MODEL or ""


def extract_plan_json(content: str) -> str:
    """Keep planner output to the first JSON-looking block."""
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
                    return content[start:idx + 1].strip()

    return content.strip()


def parse_action(content: str) -> ActionType:
    """Extracts XML tags like <run>, <write path="...">, <think>, <finish> with robust fallback handling."""
    matches = []

    # 1. Standard Matching (with closing tags)
    # <run>
    for match in re.finditer(r'<run\s*>(.*?)</run\s*>', content, re.DOTALL | re.IGNORECASE):
        matches.append((
            match.start(),
            CmdRunAction(command=match.group(1).strip()),
        ))

    # <write path="...">
    for match in re.finditer(r'<write\s+[^>]*?path\s*=\s*(?:[\'"]([^\'"]*)[\'"]|([^\s>]+))[^>]*?>(.*?)</write\s*>', content, re.DOTALL | re.IGNORECASE):
        path = match.group(1) or match.group(2)
        matches.append((
            match.start(),
            FileWriteAction(path=path.strip(), content=match.group(3).strip()),
        ))

    # <browse>
    for match in re.finditer(r'<browse\s+[^>]*?command\s*=\s*(?:[\'"]([^\'"]*)[\'"]|([^\s>]+))[^>]*?target\s*=\s*(?:[\'"]([^\'"]*)[\'"]|([^\s>]+))[^>]*?>', content, re.IGNORECASE):
        cmd = match.group(1) or match.group(2)
        target = match.group(3) or match.group(4)
        matches.append((
            match.start(),
            BrowserAction(command=cmd.strip(), target=target.strip()),
        ))

    # <search>
    for match in re.finditer(r'<search\s*>(.*?)</search\s*>', content, re.DOTALL | re.IGNORECASE):
        matches.append((
            match.start(),
            WebSearchAction(query=match.group(1).strip()),
        ))

    # <finish>
    for match in re.finditer(r'<finish\s*>(.*?)</finish\s*>', content, re.DOTALL | re.IGNORECASE):
        matches.append((
            match.start(),
            FinishAction(message=match.group(1).strip()),
        ))

    # 2. Fallback Matching (for unclosed/truncated tags)
    if not matches:
        # Check <write>
        open_write = re.search(r'<write\s+[^>]*?path\s*=\s*(?:[\'"]([^\'"]*)[\'"]|([^\s>]+))[^>]*?>', content, re.IGNORECASE)
        if open_write:
            path = open_write.group(1) or open_write.group(2)
            file_content = content[open_write.end():].strip()
            file_content = re.sub(r'</write\s*>\s*$', '', file_content, flags=re.IGNORECASE)
            return FileWriteAction(path=path.strip(), content=file_content)

        # Check <run>
        open_run = re.search(r'<run\s*>', content, re.IGNORECASE)
        if open_run:
            cmd = content[open_run.end():].strip()
            cmd = re.sub(r'</run\s*>\s*$', '', cmd, flags=re.IGNORECASE)
            return CmdRunAction(command=cmd)

        # Check <search>
        open_search = re.search(r'<search\s*>', content, re.IGNORECASE)
        if open_search:
            q = content[open_search.end():].strip()
            q = re.sub(r'</search\s*>\s*$', '', q, flags=re.IGNORECASE)
            return WebSearchAction(query=q)

        # Check <finish>
        open_finish = re.search(r'<finish\s*>', content, re.IGNORECASE)
        if open_finish:
            msg = content[open_finish.end():].strip()
            msg = re.sub(r'</finish\s*>\s*$', '', msg, flags=re.IGNORECASE)
            return FinishAction(message=msg)

    if matches:
        return min(matches, key=lambda item: item[0])[1]

    return UnknownAction(content=content)


async def plan_node(state: AgentState) -> AgentState:
    llm = _resolve_llm(state, role="planner")
    chain = plan_prompt | llm
    
    # We expect the first message to be the SRS text
    srs = state.get('messages', [HumanMessage(content="")])[0].content
    judge_feedback = state.get('judge_feedback', '')
    
    response = await chain.ainvoke({
        'srs_text': srs,
        'judge_feedback': judge_feedback
    })
    content = response.content if isinstance(response.content, str) else str(response.content)
    plan_json = extract_plan_json(content)

    # Update memory with plan
    session_id = state.get('session_id', '')
    memory = _get_memory_manager(session_id)
    memory.update_working_memory(plan=plan_json)

    return {
        'plan': plan_json,
        'status': 'setup_env',
        'messages': [AIMessage(content=f'Plan ready:\n{plan_json}')]
    }


async def setup_environment_node(state: AgentState) -> AgentState:
    """
    Analyze the plan's tech_stack/environment and prepare the Docker sandbox.
    
    This node:
    1. Parses the plan JSON for tech_stack and environment fields
    2. Detects what runtimes/tools are needed
    3. Installs missing packages into the sandbox
    4. Reports available tools to the implement node
    """
    import json as _json

    session_id = state.get('session_id', '')
    plan_str = state.get('plan', '{}')
    
    # Parse the plan
    try:
        plan = _json.loads(plan_str)
    except _json.JSONDecodeError:
        logger.warning("setup_env_plan_parse_failed", session_id=session_id)
        plan = {}

    tech_stack = plan.get('tech_stack', {})
    environment = plan.get('environment', {})
    runtimes_needed = environment.get('runtime', [])
    system_packages = environment.get('system_packages', [])
    global_tools = environment.get('global_tools', [])

    # ── Auto-detect from tech_stack if environment block is missing ──
    frontend = tech_stack.get('frontend', 'none')
    backend = tech_stack.get('backend', 'none')
    database = tech_stack.get('database', 'none')
    language = tech_stack.get('language', '')

    if not runtimes_needed:
        runtimes_needed = []
        if frontend in ('react', 'vue', 'angular', 'next', 'svelte') or language in ('javascript', 'typescript', 'abap'):
            runtimes_needed.append('node')
        if backend in ('fastapi', 'flask', 'django') or language == 'python':
            runtimes_needed.append('python3')
        if backend == 'spring_boot' or language == 'java':
            runtimes_needed.append('java')
        if language == 'go':
            runtimes_needed.append('go')
        if not runtimes_needed:
            runtimes_needed = ['python3']  # fallback: always have python

    if not system_packages:
        if database == 'postgresql':
            system_packages.append('postgresql-client')
        elif database == 'mongodb':
            system_packages.append('mongodb-clients')
        elif database == 'mysql':
            system_packages.append('default-mysql-client')

    # ── Get the sandbox and install what's needed ──
    setup_log = []
    runtime = DockerRuntime.get(session_id)
    
    # 1. Probe existing tools
    probe_cmd = "echo '--- VERSIONS ---' && python3 --version 2>/dev/null && node --version 2>/dev/null && npm --version 2>/dev/null && java -version 2>/dev/null && go version 2>/dev/null; echo '--- END ---'"
    probe_result = await runtime.execute(CmdRunAction(command=probe_cmd))
    existing_tools = probe_result.get('output', '')
    setup_log.append(f"Existing tools:\n{existing_tools}")
    
    # 2. Install system packages if needed
    pkgs_to_install = []
    if system_packages:
        pkgs_to_install.extend(system_packages)
    
    # Check if Java is needed but missing
    if 'java' in runtimes_needed and 'java version' not in existing_tools and 'openjdk' not in existing_tools:
        pkgs_to_install.extend(['default-jdk', 'maven'])
    
    # Check if Go is needed but missing
    if 'go' in runtimes_needed and 'go version' not in existing_tools:
        pkgs_to_install.append('golang')
    
    if pkgs_to_install:
        install_cmd = f"apt-get update -qq && apt-get install -y -qq {' '.join(pkgs_to_install)} 2>&1 | tail -5"
        logger.info("setup_env_installing_packages", session_id=session_id, packages=pkgs_to_install)
        result = await runtime.execute(CmdRunAction(command=install_cmd))
        if result.get('exit_code', 1) == 0:
            setup_log.append(f"Installed system packages: {', '.join(pkgs_to_install)}")
        else:
            setup_log.append(f"Warning: Some packages failed to install: {result.get('output', '')[:200]}")

    # 3. Install global npm tools if needed
    if global_tools and 'node' in runtimes_needed:
        for tool in global_tools:
            result = await runtime.execute(CmdRunAction(command=f"npm install -g {tool} 2>&1 | tail -3"))
            if result.get('exit_code', 1) == 0:
                setup_log.append(f"Installed global tool: {tool}")
            else:
                setup_log.append(f"Warning: Failed to install {tool}")

    # 4. Build the environment summary for the LLM
    env_summary_parts = [
        f"Runtime(s): {', '.join(runtimes_needed)}",
        f"Frontend stack: {frontend}",
        f"Backend stack: {backend}",
        f"Database: {database}",
        f"Language: {language}",
    ]
    if system_packages:
        env_summary_parts.append(f"System packages installed: {', '.join(system_packages)}")
    if global_tools:
        env_summary_parts.append(f"Global tools installed: {', '.join(global_tools)}")
    
    # Final probe to confirm
    final_probe = await runtime.execute(CmdRunAction(
        command="echo 'node:' $(node --version 2>/dev/null || echo 'N/A') '| npm:' $(npm --version 2>/dev/null || echo 'N/A') '| python:' $(python3 --version 2>/dev/null || echo 'N/A') '| java:' $(java -version 2>&1 | head -1 || echo 'N/A') '| go:' $(go version 2>/dev/null || echo 'N/A')"
    ))
    env_summary_parts.append(f"Verified versions: {final_probe.get('output', 'unknown')}")

    environment_info = '\n'.join(env_summary_parts)
    
    logger.info("setup_env_complete", session_id=session_id, environment=environment_info)

    return {
        'environment_info': environment_info,
        'status': 'implement',
        'messages': [AIMessage(content=f'[Environment Setup Complete]\n{environment_info}')],
    }


async def implement_node(state: AgentState) -> AgentState:
    llm = _resolve_llm(state, role="coder")
    model_name = _get_model_name(state)
    session_id = state.get('session_id', '')
    chain = implement_prompt | llm
    
    # ── Phase 1: Context Management ────────────────────────────────────
    ctx_manager = ContextManager(model=model_name)
    messages = state.get('messages', [])
    pruned_messages = ctx_manager.prune_messages(messages)

    # Log token stats
    stats = ctx_manager.get_context_stats(pruned_messages)
    if stats.get("over_budget"):
        logger.warning(
            "context_over_budget",
            session_id=session_id,
            usage_percent=stats["usage_percent"],
        )

    # ── Phase 2: Error Analysis ────────────────────────────────────────
    last_obs_obj = state.get('last_obs')
    last_error = ''
    error_analysis_text = ''
    
    if last_obs_obj:
        exit_code = getattr(last_obs_obj, 'exit_code', 0)
        if exit_code != 0:
            raw_output = getattr(last_obs_obj, 'output', '')
            last_error = raw_output

            # Analyze the error
            parsed_error = _error_analyzer.analyze(raw_output, exit_code)
            error_analysis_text = _error_analyzer.format_for_prompt(parsed_error)

            # Track in memory
            memory = _get_memory_manager(session_id)
            memory.update_working_memory(
                error_seen=f"{parsed_error.category.value}: {parsed_error.message[:100]}"
            )

            # Check if retry is worthwhile
            retries = state.get('retries', 0)
            if not _error_analyzer.should_retry(parsed_error, retries):
                logger.warning(
                    "error_not_retryable",
                    session_id=session_id,
                    category=parsed_error.category.value,
                    retries=retries,
                )

            logger.info(
                "implement_with_error_analysis",
                session_id=session_id,
                category=parsed_error.category.value,
                severity=parsed_error.severity.value,
            )
    
    # ── Phase 3: Workspace Context ─────────────────────────────────────
    workspace_context = state.get('workspace_summary', '')
    if not workspace_context:
        # Try to index the workspace on first implement call
        try:
            runtime = DockerRuntime.get(session_id) if session_id else None
            if runtime:
                indexer = WorkspaceIndexer("/workspace")
                # Run indexing in the sandbox container
                result = await runtime.execute(CmdRunAction(
                    command="find /workspace -maxdepth 3 -type f -not -path '*/node_modules/*' -not -path '*/.git/*' | head -100"
                ))
                if result.get('exit_code') == 0 and result.get('output'):
                    file_list = result['output'].strip()
                    workspace_context = f"Current workspace files:\n{file_list}"
        except Exception as e:
            logger.debug("workspace_index_skipped", reason=str(e))

    # Small courtesy delay — rate limiting is handled by GroqKeyPool
    await asyncio.sleep(0.5)
    
    response = await chain.ainvoke({
        'plan': state.get('plan', ''),
        'messages': pruned_messages,
        'error': last_error,
        'workspace_context': workspace_context,
        'error_analysis': error_analysis_text,
        'environment_info': state.get('environment_info', 'No environment info available. Python3 and Node.js are pre-installed.'),
        'research_context': state.get('research_context', 'No web research available. Use <search>query</search> to look up information.'),
    })
    
    content = response.content if isinstance(response.content, str) else str(response.content)
    action = parse_action(content)

    # Track file writes in memory
    if isinstance(action, FileWriteAction):
        memory = _get_memory_manager(session_id)
        memory.update_working_memory(file_written=action.path)

    # If the agent decided to finish
    if isinstance(action, FinishAction):
        logger.info("implement_finish", session_id=session_id, message=action.message)
        return {
            'messages': [AIMessage(content=content)],
            'status': 'validate',
            '_action': action,
            'token_count': count_message_tokens(pruned_messages),
        }
    
    # Log the action being taken
    action_type = type(action).__name__
    logger.info("implement_action", session_id=session_id, action=action_type)
        
    return {
        'messages': [AIMessage(content=content)],
        'status': 'execute',
        '_action': action,
        'token_count': count_message_tokens(pruned_messages),
        'last_error_analysis': error_analysis_text if error_analysis_text else None,
    }


async def execute_node(state: AgentState) -> AgentState:
    session_id = state.get('session_id')
    if not session_id:
        raise RuntimeError("session_id is required for execution")
    runtime = DockerRuntime.get(session_id)
    action = state.get('_action')
    if action is None:
        action = UnknownAction(content='')
    
    if isinstance(action, UnknownAction):
        obs = ErrorObservation(output='Error: Could not parse a valid action (<run>, <write>, <finish>).', exit_code=1)
        logger.error("execute_unknown_action", session_id=session_id)
        return {
            'last_obs': obs,
            'retries': state.get('retries', 0) + 1,
            'messages': [HumanMessage(content='Observation: Invalid action format. You MUST use exactly ONE of the XML tags: <run>, <write>, or <finish>. Example: <run>ls</run>. DO NOT use markdown code blocks or plain text.')],
        }
    
    # Log the action being executed
    action_type = type(action).__name__
    action_detail = ''
    if isinstance(action, CmdRunAction):
        action_detail = action.command[:100]
    elif isinstance(action, FileWriteAction):
        action_detail = action.path
    elif isinstance(action, WebSearchAction):
        action_detail = action.query[:100]
    logger.info("execute_start", session_id=session_id, action=action_type, detail=action_detail)

    # ── WebSearchAction: do live web search (no Docker needed) ──────────
    if isinstance(action, WebSearchAction):
        from .research_node import search_for_error

        tech_context = ''
        plan_str = state.get('plan', '{}')
        try:
            import json as _json
            plan = _json.loads(plan_str)
            tech_stack = plan.get('tech_stack', {})
            tech_context = f"{tech_stack.get('frontend', '')} {tech_stack.get('backend', '')} {tech_stack.get('language', '')}".strip()
        except Exception:
            pass

        search_result = await search_for_error(action.query, tech_context)

        obs = CmdOutputObservation(output=search_result, exit_code=0)
        logger.info("execute_search", session_id=session_id, query=action.query[:80])

        return {
            'last_obs': obs,
            'retries': state.get('retries', 0),
            'messages': [HumanMessage(
                content=f"Observation (web search for '{action.query}'):\n{search_result}"
            )],
        }
        
    obs_dict = await runtime.execute(action)
    
    # ── Phase 2: Error analysis on execution results ────────────────────
    if 'error' in obs_dict:
        raw_output = obs_dict['output']
        exit_code = obs_dict.get('exit_code', 1)

        # Analyze the error
        parsed_error = _error_analyzer.analyze(raw_output, exit_code)
        error_context = _error_analyzer.format_for_prompt(parsed_error)

        obs = ErrorObservation(output=obs_dict['output'], exit_code=exit_code)
        logger.error(
            "execute_error",
            session_id=session_id,
            category=parsed_error.category.value,
            exit_code=obs.exit_code,
            output=obs.output[:200],
        )

        retries = state.get('retries', 0) + 1

        return {
            'last_obs': obs,
            'retries': retries,
            'messages': [HumanMessage(
                content=f"Observation:\nExit code: {obs.exit_code}\n\n{error_context}"
            )],
            'last_error_analysis': error_context,
            'error_history': (state.get('error_history') or []) + [{
                'category': parsed_error.category.value,
                'severity': parsed_error.severity.value,
                'message': parsed_error.message[:200],
                'file': parsed_error.file,
                'line': parsed_error.line,
            }],
        }

    elif isinstance(action, BrowserAction):
        obs = BrowserObservation(output=obs_dict.get('output', ''), content=obs_dict.get('content', ''), exit_code=obs_dict.get('exit_code', 0))
        logger.info("execute_browser", session_id=session_id, exit_code=obs.exit_code)
    else:
        obs = CmdOutputObservation(output=obs_dict.get('output', ''), exit_code=obs_dict.get('exit_code', 0))
        if obs.exit_code == 0:
            logger.info("execute_success", session_id=session_id, output=obs.output[:100])
        else:
            # Non-zero exit code but not in 'error' key — still analyze
            parsed_error = _error_analyzer.analyze(obs.output, obs.exit_code)

            logger.error(
                "execute_failed",
                session_id=session_id,
                category=parsed_error.category.value,
                exit_code=obs.exit_code,
                output=obs.output[:200],
            )

            error_context = _error_analyzer.format_for_prompt(parsed_error)

            return {
                'last_obs': obs,
                'retries': state.get('retries', 0) + 1,
                'messages': [HumanMessage(
                    content=f"Observation:\nExit code: {obs.exit_code}\n\n{error_context}"
                )],
                'last_error_analysis': error_context,
            }
        
    retries = state.get('retries', 0) + (1 if getattr(obs, 'exit_code', 0) != 0 else 0)
    
    # ── Phase 3: Update workspace summary after successful actions ──
    workspace_update = {}
    if obs_dict.get('exit_code', 0) == 0:
        # Refresh workspace file list
        try:
            result = await runtime.execute(CmdRunAction(
                command="find /workspace -maxdepth 3 -type f -not -path '*/node_modules/*' -not -path '*/.git/*' | head -100"
            ))
            if result.get('exit_code') == 0 and result.get('output'):
                workspace_update['workspace_summary'] = f"Current workspace files:\n{result['output'].strip()}"
        except Exception:
            pass

    raw_output = getattr(obs, 'output', '')
    # Truncate large outputs (like npm install outputs) to prevent context bloat
    lines = raw_output.splitlines()
    if len(lines) > 40:
        first_part = lines[:15]
        last_part = lines[-20:]
        omitted = len(lines) - 35
        truncated_output = "\n".join(first_part) + f"\n\n... [output truncated for brevity, {omitted} lines omitted] ...\n\n" + "\n".join(last_part)
    else:
        truncated_output = raw_output

    result_state: dict = {
        'last_obs': obs,
        'retries': retries,
        'messages': [HumanMessage(content=f"Observation:\nExit code: {getattr(obs, 'exit_code', 0)}\nOutput:\n{truncated_output}")],
    }
    if workspace_update:
        result_state.update(workspace_update)
    return result_state


async def validate_node(state: AgentState) -> AgentState:
    session_id = state.get('session_id')
    if not session_id:
        raise RuntimeError("session_id is required for validation")
    runtime = DockerRuntime.get(session_id)
    
    # Check if any app is running on common ports
    app_started = False
    app_url = None
    error_output = []
    
    # Try common development ports
    for port in [3000, 5173, 8000, 8080, 4200, 5000]:
        try:
            health = await runtime.health_check(port=port)
            if health.get('healthy'):
                app_started = True
                app_url = health.get('url')
                logger.info("app_validated", session_id=session_id, port=port, url=app_url)
                break
        except Exception as e:
            error_output.append(f"Port {port}: {str(e)}")
    
    # If no app found, check if there are any running processes
    if not app_started:
        result = await runtime.execute(CmdRunAction(command="ps aux | grep -E 'node|npm|python|flask|django' | grep -v grep"))
        if result.get('exit_code') == 0 and result.get('output'):
            # Process is running but not accessible
            obs = ValidatedObservation(
                output=f"App process running but not accessible on common ports.\nProcesses:\n{result['output']}\n\nPort checks:\n" + "\n".join(error_output),
                exit_code=1,
                app_started=False
            )
        else:
            # No app running at all
            obs = ValidatedObservation(
                output=f"No app process found running.\nPort checks:\n" + "\n".join(error_output),
                exit_code=1,
                app_started=False
            )
    else:
        obs = ValidatedObservation(
            output=f'App is running and accessible at {app_url}',
            exit_code=0,
            app_started=True
        )
    
    return {
        'last_obs': obs,
        'status': 'done' if obs.app_started else 'error',
        'messages': [AIMessage(content=f'Validation: {obs.output}')]
    }
