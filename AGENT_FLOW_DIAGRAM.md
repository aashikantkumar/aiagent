# Agent Flow Diagram: Error Handling & Debugging

## Complete Agent Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER SENDS MESSAGE                       │
│                    "Create a To-Do app"                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │   PLAN NODE    │
                    │                │
                    │ • Analyze SRS  │
                    │ • Create JSON  │
                    │ • List files   │
                    └────────┬───────┘
                             │
                             ▼
                    ┌────────────────┐
                    │ IMPLEMENT NODE │◄─────────────────┐
                    │                │                  │
                    │ • Read plan    │                  │
                    │ • Read error   │◄─────┐           │
                    │ • Generate fix │      │           │
                    │ • Output action│      │           │
                    └────────┬───────┘      │           │
                             │              │           │
                             ▼              │           │
                    ┌────────────────┐      │           │
                    │  EXECUTE NODE  │      │           │
                    │                │      │           │
                    │ • Run command  │      │           │
                    │ • Write file   │      │           │
                    │ • Check result │      │           │
                    └────────┬───────┘      │           │
                             │              │           │
                             ▼              │           │
                    ┌────────────────┐      │           │
                    │  CHECK RESULT  │      │           │
                    │                │      │           │
                    │ exit_code == 0?│      │           │
                    └────────┬───────┘      │           │
                             │              │           │
                    ┌────────┴────────┐     │           │
                    │                 │     │           │
                    ▼                 ▼     │           │
              ┌─────────┐       ┌─────────┐│           │
              │ SUCCESS │       │  ERROR  ││           │
              └────┬────┘       └────┬────┘│           │
                   │                 │     │           │
                   │                 ▼     │           │
                   │          ┌──────────┐ │           │
                   │          │ Retries  │ │           │
                   │          │  < 5?    │ │           │
                   │          └────┬─────┘ │           │
                   │               │       │           │
                   │      ┌────────┴───┐   │           │
                   │      │            │   │           │
                   │      ▼            ▼   │           │
                   │   ┌─────┐    ┌───────┴───┐       │
                   │   │ YES │    │    NO     │       │
                   │   └──┬──┘    │ MAX RETRY │       │
                   │      │       └─────┬─────┘       │
                   │      │             │             │
                   │      └─────────────┘             │
                   │                    │             │
                   │                    ▼             │
                   │              ┌──────────┐        │
                   │              │   END    │        │
                   │              │ (Failed) │        │
                   │              └──────────┘        │
                   │                                  │
                   ▼                                  │
          ┌────────────────┐                         │
          │ More files to  │                         │
          │    write?      │                         │
          └────────┬───────┘                         │
                   │                                  │
          ┌────────┴────────┐                        │
          │                 │                        │
          ▼                 ▼                        │
     ┌────────┐       ┌──────────┐                  │
     │  YES   │       │    NO    │                  │
     └───┬────┘       └────┬─────┘                  │
         │                 │                        │
         └─────────────────┘                        │
                                                    │
                   ▼                                │
          ┌────────────────┐                        │
          │ VALIDATE NODE  │                        │
          │                │                        │
          │ • Check if app │                        │
          │   is running   │                        │
          │ • Test preview │                        │
          └────────┬───────┘                        │
                   │                                │
                   ▼                                │
          ┌────────────────┐                        │
          │  App started?  │                        │
          └────────┬───────┘                        │
                   │                                │
          ┌────────┴────────┐                       │
          │                 │                       │
          ▼                 ▼                       │
     ┌────────┐       ┌──────────┐                 │
     │  PASS  │       │   FAIL   │                 │
     └───┬────┘       └────┬─────┘                 │
         │                 │                       │
         │                 └───────────────────────┘
         │
         ▼
   ┌──────────┐
   │   END    │
   │(Success) │
   └──────────┘
```

## Error Handling Examples

### Example 1: Missing Dependency

```
User: "Create a Node.js Express app"

┌─────────────────────────────────────────────────────────────┐
│ PLAN NODE                                                    │
│ Output: {                                                    │
│   "files": ["package.json", "server.js"],                   │
│   "tech": "Node.js + Express"                               │
│ }                                                            │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ IMPLEMENT NODE (Iteration 1)                                │
│ Action: <write path='package.json'>                         │
│ {                                                            │
│   "name": "express-app",                                    │
│   "dependencies": {}  ← MISSING EXPRESS                     │
│ }                                                            │
│ </write>                                                     │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ EXECUTE NODE                                                 │
│ Command: Write package.json                                 │
│ Result: ✓ Success (exit_code=0)                            │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ IMPLEMENT NODE (Iteration 2)                                │
│ Action: <write path='server.js'>                            │
│ const express = require('express');                         │
│ const app = express();                                      │
│ app.listen(3000);                                           │
│ </write>                                                     │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ EXECUTE NODE                                                 │
│ Command: Write server.js                                    │
│ Result: ✓ Success (exit_code=0)                            │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ IMPLEMENT NODE (Iteration 3)                                │
│ Action: <run>npm install</run>                              │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ EXECUTE NODE                                                 │
│ Command: npm install                                        │
│ Result: ✓ Success (exit_code=0)                            │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ IMPLEMENT NODE (Iteration 4)                                │
│ Action: <run>node server.js</run>                           │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ EXECUTE NODE                                                 │
│ Command: node server.js                                     │
│ Result: ✗ ERROR (exit_code=1)                              │
│ Output: "Error: Cannot find module 'express'"              │
│         "Require stack: /workspace/server.js"               │
└─────────────────────────────────────────────────────────────┘
                             ↓
                    ┌────────────────┐
                    │ ROUTE: ERROR   │
                    │ Retries: 1/5   │
                    └────────┬───────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ IMPLEMENT NODE (Iteration 5) ← DEBUGGING                    │
│ Error received: "Cannot find module 'express'"             │
│                                                              │
│ Agent analyzes:                                             │
│ "The error shows express is not installed. I need to add   │
│  it to package.json dependencies."                          │
│                                                              │
│ Action: <write path='package.json'>                         │
│ {                                                            │
│   "name": "express-app",                                    │
│   "dependencies": {                                         │
│     "express": "^4.18.0"  ← FIXED                          │
│   }                                                          │
│ }                                                            │
│ </write>                                                     │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ EXECUTE NODE                                                 │
│ Command: Write package.json                                 │
│ Result: ✓ Success (exit_code=0)                            │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ IMPLEMENT NODE (Iteration 6)                                │
│ Action: <run>npm install</run>                              │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ EXECUTE NODE                                                 │
│ Command: npm install                                        │
│ Result: ✓ Success (exit_code=0)                            │
│ Output: "added 57 packages"                                 │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ IMPLEMENT NODE (Iteration 7)                                │
│ Action: <run>node server.js &</run>                         │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ EXECUTE NODE                                                 │
│ Command: node server.js &                                   │
│ Result: ✓ Success (exit_code=0)                            │
│ Output: "Server listening on port 3000"                     │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ IMPLEMENT NODE (Iteration 8)                                │
│ Action: <finish>Express app is running on port 3000</finish>│
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ VALIDATE NODE                                                │
│ Check: Is app running?                                      │
│ Result: ✓ PASS                                              │
└─────────────────────────────────────────────────────────────┘
                             ↓
                        ┌────────┐
                        │  END   │
                        │SUCCESS │
                        └────────┘
```

### Example 2: Syntax Error

```
User: "Create a Python Flask app"

[... Plan and initial implementation ...]

┌─────────────────────────────────────────────────────────────┐
│ IMPLEMENT NODE                                               │
│ Action: <write path='app.py'>                               │
│ from flask import Flask                                     │
│ app = Flask(__name__)                                       │
│                                                              │
│ @app.route('/')                                             │
│ def home()  ← MISSING COLON                                 │
│     return 'Hello'                                          │
│ </write>                                                     │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ EXECUTE NODE                                                 │
│ Command: python app.py                                      │
│ Result: ✗ ERROR (exit_code=1)                              │
│ Output: "SyntaxError: invalid syntax (app.py, line 5)"     │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ IMPLEMENT NODE ← DEBUGGING                                   │
│ Error: "SyntaxError: invalid syntax (app.py, line 5)"      │
│                                                              │
│ Agent analyzes:                                             │
│ "Line 5 has a syntax error. The function definition is     │
│  missing a colon after the parentheses."                    │
│                                                              │
│ Action: <write path='app.py'>                               │
│ from flask import Flask                                     │
│ app = Flask(__name__)                                       │
│                                                              │
│ @app.route('/')                                             │
│ def home():  ← FIXED                                        │
│     return 'Hello'                                          │
│ </write>                                                     │
└─────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────┐
│ EXECUTE NODE                                                 │
│ Command: python app.py                                      │
│ Result: ✓ Success (exit_code=0)                            │
│ Output: "Running on http://127.0.0.1:5000"                 │
└─────────────────────────────────────────────────────────────┘
                             ↓
                        ┌────────┐
                        │SUCCESS │
                        └────────┘
```

## Key Points

### ✅ Automatic Error Detection
- Every command execution is checked (exit_code)
- Errors are captured (stdout + stderr)
- Error context is preserved in state

### ✅ Automatic Debugging
- Error message passed to implement node
- Agent analyzes error using LLM
- Agent generates fix automatically
- Fix is executed immediately

### ✅ Retry Mechanism
- Up to 5 retry attempts
- Each retry gets full error context
- Retry counter prevents infinite loops

### ✅ Validation Loop
- After all files written, validate app
- If validation fails, go back to implement
- Keep trying until app starts

### ⚠️ Limitations
- Only detects build/start errors
- Doesn't monitor runtime logs
- Doesn't test UI functionality
- Limited to 5 retries per error

## Summary

**YES, the agent automatically detects and fixes errors!**

The error handling flow:
1. Execute command/write file
2. Check exit code
3. If error → capture message
4. Pass error to implement node
5. Agent analyzes and generates fix
6. Execute fix
7. Repeat until success or max retries

This happens automatically without user intervention.
