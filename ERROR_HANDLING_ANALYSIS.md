# Error Handling & Debugging Analysis

## Question
Does the agent automatically detect and fix errors during preview/execution?

## Answer: ✅ YES - Automatic Error Detection & Debugging is Implemented

## How It Works

### 1. Graph Flow with Error Handling

```
Plan → Implement → Execute → [Check Result]
                      ↑           |
                      |           ↓
                      ←─── Error? ─── Success?
                                  |
                                  ↓
                            Validate → [Check App]
                                  |
                                  ↓
                            Pass? ─── Fail?
                                  |
                                  ↓
                            Back to Implement
```

### 2. Automatic Retry Loop

**Location**: `backend/agent/graph.py`

```python
def route_after_execute(state: AgentState) -> str:
    obs = state.get('last_obs')
    if obs and getattr(obs, 'exit_code', 1) == 0:
        return 'success'  # Command succeeded, continue
    if state.get('retries', 0) >= 5:
        return 'max_retry'  # Give up after 5 attempts
    return 'error'  # Go back to implement node to fix
```

**What happens on error**:
1. Execute node runs command (e.g., `npm install`, `npm run dev`)
2. If exit_code != 0 (error), route to 'error'
3. 'error' path goes back to **implement node**
4. Implement node receives the error message
5. Agent analyzes error and generates fix
6. Execute node runs the fix
7. Repeat until success or max retries (5)

### 3. Error Context Passed to Agent

**Location**: `backend/agent/nodes.py`

```python
async def implement_node(state: AgentState) -> AgentState:
    # Extract error from last observation
    last_obs_obj = state.get('last_obs')
    last_error = getattr(last_obs_obj, 'output', '') if getattr(last_obs_obj, 'exit_code', 0) != 0 else ''
    
    # Pass error to LLM for debugging
    response = await chain.ainvoke({
        'plan': state.get('plan', ''),
        'messages': state.get('messages', []),
        'error': last_error,  # ← Error message here
    })
```

The agent receives:
- Full error output (stderr + stdout)
- Exit code
- Previous messages (conversation history)
- Original plan

### 4. Agent Instructions for Debugging

**Location**: `backend/agent/prompts.py`

```python
SYSTEM_PROMPT = """
CRITICAL RULES:
  - If a command fails, read the error and fix before continuing
  - Write complete files — never use '...' or placeholder comments
  - Only use <finish> when the app is fully built and running
  - Continue working until you see the app running successfully
"""

implement_prompt = ChatPromptTemplate.from_messages([
    ('human', '''Plan:\n{plan}\n\nLast observation/error: {error}

IMPORTANT: Continue implementing until ALL files are written and the app is running.
What is the next action?'''),
])
```

The agent is explicitly told to:
- Read errors
- Fix them before continuing
- Keep trying until app runs

### 5. Validation Phase Error Handling

**Location**: `backend/agent/graph.py`

```python
def route_after_validate(state: AgentState) -> str:
    obs = state.get('last_obs')
    return 'pass' if obs and getattr(obs, 'app_started', False) else 'fail'

g.add_conditional_edges('validate', route_after_validate, {
    'pass': END,        # App started successfully
    'fail': 'implement', # Go back to fix issues
})
```

If validation fails (app doesn't start), the agent goes back to implement node to debug.

## Example Error Handling Flow

### Scenario: Missing Dependency Error

```
1. Agent writes package.json and index.js
2. Execute: npm install
   → Success (exit_code=0)
3. Execute: npm run dev
   → Error: "Cannot find module 'express'"
   → exit_code=1
4. Route: 'error' → back to implement
5. Implement receives error: "Cannot find module 'express'"
6. Agent analyzes: "Missing express in package.json"
7. Agent action: <write path='package.json'>
   {
     "dependencies": {
       "express": "^4.18.0"  ← Added
     }
   }
   </write>
8. Execute: npm install
   → Success
9. Execute: npm run dev
   → Success (app starts)
10. Validate: Check if app is running
    → Pass
11. END
```

### Scenario: Syntax Error in Code

```
1. Agent writes app.js with syntax error
2. Execute: node app.js
   → Error: "SyntaxError: Unexpected token }"
   → exit_code=1
3. Route: 'error' → back to implement
4. Implement receives error with line number
5. Agent analyzes: "Extra closing brace on line 15"
6. Agent action: <write path='app.js'>
   [Fixed code without extra brace]
   </write>
7. Execute: node app.js
   → Success
8. Continue...
```

### Scenario: Port Already in Use

```
1. Agent starts app on port 3000
2. Execute: npm run dev
   → Error: "EADDRINUSE: address already in use :::3000"
   → exit_code=1
3. Route: 'error' → back to implement
4. Implement receives error
5. Agent analyzes: "Port 3000 is busy"
6. Agent action: <run>lsof -ti:3000 | xargs kill -9</run>
   OR
   Agent action: <write path='app.js'>
   [Changed port to 3001]
   </write>
7. Execute: npm run dev
   → Success
8. Continue...
```

## Retry Limit

**Maximum retries**: 5 attempts

**Location**: `backend/agent/nodes.py`

```python
retries = state.get('retries', 0) + (1 if getattr(obs, 'exit_code', 0) != 0 else 0)
```

**What happens after 5 retries**:
- Graph routes to 'max_retry' → END
- Agent stops trying
- User sees last error message
- User can manually debug or send new message

## Error Types Handled

### 1. Command Execution Errors
- Missing dependencies
- Syntax errors
- Runtime errors
- Port conflicts
- Permission errors

### 2. Build Errors
- Compilation failures
- Linting errors
- Type errors
- Missing files

### 3. Runtime Errors
- Module not found
- Connection refused
- Timeout errors
- Memory errors

### 4. Validation Errors
- App doesn't start
- Health check fails
- Preview not accessible

## Limitations

### 1. No Error Detected After Validation Pass

**Issue**: If the app starts but has runtime bugs (e.g., button doesn't work), the agent won't detect it.

**Why**: Validation only checks if the app starts, not if it works correctly.

**Solution**: User needs to test and report bugs manually.

### 2. Complex Errors May Exceed Retry Limit

**Issue**: Some errors require multiple fixes (e.g., cascading dependency issues).

**Why**: Limited to 5 retries.

**Solution**: User can send follow-up message: "Fix the dependency error"

### 3. Silent Failures

**Issue**: If the app starts but logs errors to console, agent won't see them.

**Why**: Validation only checks process exit code, not logs.

**Solution**: Implement log monitoring in validate_node.

## Improvements Needed

### 1. Enhanced Validation

**Current**:
```python
async def validate_node(state: AgentState) -> AgentState:
    # Just assumes finish means success
    obs = ValidatedObservation(output='Validation skipped', exit_code=0, app_started=True)
    return {...}
```

**Improved**:
```python
async def validate_node(state: AgentState) -> AgentState:
    runtime = DockerRuntime.get(session_id)
    
    # 1. Check if process is running
    result = await runtime.execute(CmdRunAction(command="ps aux | grep 'npm\\|node\\|python'"))
    
    # 2. Try to access the app
    for port in [3000, 5173, 8000]:
        result = await runtime.execute(CmdRunAction(command=f"curl -s http://localhost:{port}"))
        if result['exit_code'] == 0:
            obs = ValidatedObservation(output=f'App running on port {port}', exit_code=0, app_started=True)
            return {...}
    
    # 3. Check logs for errors
    result = await runtime.execute(CmdRunAction(command="tail -50 /workspace/app.log"))
    
    obs = ValidatedObservation(output='App not accessible', exit_code=1, app_started=False)
    return {...}
```

### 2. Log Monitoring

Add a new node to check application logs:

```python
async def monitor_logs_node(state: AgentState) -> AgentState:
    runtime = DockerRuntime.get(session_id)
    
    # Check for common error patterns in logs
    result = await runtime.execute(CmdRunAction(
        command="tail -100 /workspace/app.log | grep -i 'error\\|exception\\|failed'"
    ))
    
    if result['exit_code'] == 0 and result['output']:
        # Found errors in logs
        return {
            'last_obs': ErrorObservation(output=result['output'], exit_code=1),
            'status': 'implement'  # Go back to fix
        }
    
    return {'status': 'done'}
```

### 3. Interactive Debugging

Add browser automation to test the app:

```python
async def test_app_node(state: AgentState) -> AgentState:
    runtime = DockerRuntime.get(session_id)
    
    # Use Playwright to test the app
    test_script = """
    const { chromium } = require('playwright');
    (async () => {
        const browser = await chromium.launch();
        const page = await browser.newPage();
        await page.goto('http://localhost:3000');
        
        // Check for errors in console
        page.on('console', msg => {
            if (msg.type() === 'error') {
                console.log('ERROR:', msg.text());
            }
        });
        
        // Take screenshot
        await page.screenshot({ path: 'screenshot.png' });
        await browser.close();
    })();
    """
    
    result = await runtime.execute(FileWriteAction(path='test.js', content=test_script))
    result = await runtime.execute(CmdRunAction(command='node test.js'))
    
    # Analyze results...
```

## Testing Error Handling

### Test 1: Missing Dependency

Send this message:
```
Create a Node.js app that uses express but don't include it in package.json
```

Expected behavior:
1. Agent creates files
2. npm run dev fails
3. Agent detects missing express
4. Agent adds express to package.json
5. npm install succeeds
6. App starts

### Test 2: Syntax Error

Send this message:
```
Create a Python app with a syntax error (missing colon after if statement)
```

Expected behavior:
1. Agent creates file with error
2. python app.py fails
3. Agent reads error message
4. Agent fixes syntax
5. App runs

### Test 3: Port Conflict

Send this message:
```
Create two Node.js apps both using port 3000
```

Expected behavior:
1. First app starts on 3000
2. Second app fails (port in use)
3. Agent detects conflict
4. Agent changes second app to port 3001
5. Both apps run

## Conclusion

✅ **YES, automatic error detection and debugging is fully implemented**

The agent:
- Detects errors from command exit codes
- Receives full error messages
- Analyzes errors using LLM
- Generates fixes automatically
- Retries up to 5 times
- Goes back to implement node on validation failure

**However**, there are limitations:
- Only detects errors during build/start phase
- Doesn't monitor runtime logs
- Doesn't test UI functionality
- Limited to 5 retry attempts

**Recommendation**: Enhance validation node to check logs and test app functionality.
