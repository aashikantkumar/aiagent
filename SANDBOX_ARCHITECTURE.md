# Sandbox Architecture: Isolated Development Environments

## Overview

Your AI Agent Builder creates **separate, isolated Docker containers** for each development session. Each container has its own:

- **Isolated filesystem** (`/workspace` directory)
- **Separate terminal** (persistent bash shell)
- **Independent processes** (Node.js, Python, etc.)
- **Exposed ports** (3000, 5173, 8000 for preview)
- **Resource limits** (CPU and memory quotas)

This is similar to how **OpenHands** and **GitHub Codespaces** work.

## How It Works

### 1. Session Creation

When a user creates a new session:

```
User clicks "New Session" 
    ↓
Frontend calls: POST /api/agent/sessions
    ↓
Backend creates:
  - Session ID (UUID)
  - Database record
  - LLM profile assignment
    ↓
Returns: { session_id: "abc-123", profile_id: "..." }
```

### 2. Container Creation (On First Message)

When the user sends the first message:

```
User sends: "Create a To-Do app"
    ↓
WebSocket connection established
    ↓
Backend calls: DockerRuntime.get(session_id)
    ↓
Docker creates NEW container:
  - Name: agent-sandbox-abc123-1779129331
  - Image: agent-sandbox:latest
  - Working dir: /workspace
  - Ports: 3000→45001, 5173→45002, 8000→45003
  - Memory: 2GB limit
  - CPU: 50% quota
  - Init: true (proper signal handling)
    ↓
Container starts with: sleep infinity
    ↓
Persistent bash shell spawned inside container
    ↓
Agent starts working in /workspace
```

### 3. Isolated Workspace Structure

Each container has its own `/workspace` directory:

```
Container: agent-sandbox-abc123-1779129331
│
├── /workspace/                    ← Isolated workspace
│   ├── package.json              ← Created by agent
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── TodoList.jsx
│   │   │   └── TodoItem.jsx
│   │   └── styles/
│   │       └── main.css
│   ├── public/
│   │   └── index.html
│   ├── node_modules/             ← Installed by agent
│   └── .gitignore
│
├── /tmp/                          ← Temporary files
├── /usr/bin/                      ← System binaries (node, npm, python)
└── /home/                         ← User home directory
```

**Key Points:**
- Each session gets a **completely separate** `/workspace`
- Files in one session **cannot** affect another session
- When container is deleted, all files are removed

### 4. How Agent Interacts with Workspace

#### A. Writing Files

```python
# Agent action
<write path='src/App.jsx'>
import React from 'react';
export default function App() {
  return <h1>Hello</h1>;
}
</write>

# Backend execution
action = FileWriteAction(path='src/App.jsx', content='...')
runtime.execute(action)
    ↓
Creates tarball with file
    ↓
Uploads to container: /workspace/src/App.jsx
    ↓
File now exists in isolated workspace
```

#### B. Running Commands

```python
# Agent action
<run>npm install</run>

# Backend execution
action = CmdRunAction(command='npm install')
runtime.execute(action)
    ↓
Sends command to persistent bash shell
    ↓
Shell executes: cd /workspace && npm install
    ↓
Captures output and exit code
    ↓
Returns: { output: "added 57 packages", exit_code: 0 }
```

#### C. Starting Applications

```python
# Agent action
<run>npm run dev &</run>

# Backend execution
Runs in background inside container
    ↓
App starts on port 3000 (inside container)
    ↓
Port 3000 mapped to host port 45001
    ↓
User can access: http://localhost:45001
```

## Container Lifecycle

### Creation

```
DockerRuntime.get(session_id)
    ↓
Check if container exists (Redis cache)
    ↓
If not exists:
  - Pull image: agent-sandbox:latest
  - Assign host ports (find unused ports)
  - Create container with resource limits
  - Start persistent bash shell
  - Save metadata to Redis
    ↓
If exists:
  - Reattach to existing container
  - Resume if paused
  - Reconnect bash shell
```

### Persistence

```
Container metadata stored in Redis:
{
  "session_id": "abc-123",
  "container_name": "agent-sandbox-abc123-1779129331",
  "container_ip": "172.17.0.5",
  "exposed_ports": [
    {"name": "app_server", "container_port": 3000, "host_port": 45001},
    {"name": "dev_server", "container_port": 5173, "host_port": 45002},
    {"name": "backend", "container_port": 8000, "host_port": 45003}
  ],
  "created_at": 1779129331
}

TTL: 24 hours (auto-expires)
```

### Cleanup

**Automatic cleanup happens when:**

1. **Container is older than 24 hours**
   ```
   Background task runs every hour
   Checks all containers in Redis
   Removes containers older than 24h
   ```

2. **Max sandbox limit reached (5 containers)**
   ```
   Before creating new container
   Count existing containers
   If >= 5: Pause oldest container
   Then create new one
   ```

3. **Manual deletion**
   ```
   User clicks "Delete Session"
   DELETE /api/agent/sandbox/{session_id}
   Container stopped and removed
   Redis metadata deleted
   ```

## Port Mapping

Each container exposes 3 ports by default:

```
Container Port  →  Host Port (auto-assigned)  →  Purpose
─────────────────────────────────────────────────────────
3000            →  45001 (example)            →  Node.js/React apps
5173            →  45002 (example)            →  Vite dev server
8000            →  45003 (example)            →  Python/Flask apps
```

**How it works:**

1. **Find unused host ports**
   ```python
   def _find_unused_port():
       with socket.socket() as s:
           s.bind(('', 0))  # Bind to any available port
           return s.getsockname()[1]
   ```

2. **Map container ports to host ports**
   ```python
   port_bindings = {
       "3000/tcp": 45001,
       "5173/tcp": 45002,
       "8000/tcp": 45003
   }
   ```

3. **Access from browser**
   ```
   Container: http://localhost:3000 (inside)
   Host: http://localhost:45001 (outside)
   ```

## Resource Limits

Each container has resource limits to prevent one session from consuming all resources:

```python
container = client.containers.run(
    image='agent-sandbox:latest',
    mem_limit='2g',              # 2GB RAM limit
    cpu_period=100000,           # CPU scheduling period
    cpu_quota=50000,             # 50% of one CPU core
    ...
)
```

**What this means:**
- Each session can use **max 2GB RAM**
- Each session can use **max 50% of one CPU core**
- If limit exceeded, container is throttled (not killed)

## File Persistence

### During Session

Files persist as long as the container is running:

```
User sends: "Create index.html"
    ↓
Agent writes: /workspace/index.html
    ↓
File exists in container
    ↓
User can download file via API
    ↓
File persists until container is deleted
```

### After Session Ends

**Option 1: Container Paused (Default)**
```
User closes browser
    ↓
Container stays running
    ↓
Files remain in /workspace
    ↓
User can reconnect later
    ↓
Files still there
```

**Option 2: Container Deleted**
```
User clicks "Delete Session"
    ↓
Container stopped and removed
    ↓
All files in /workspace are LOST
    ↓
Cannot recover files
```

**Option 3: Download Files Before Deletion**
```
GET /api/agent/sandbox/{session_id}/files
    ↓
Returns: ["index.html", "src/App.jsx", ...]
    ↓
GET /api/agent/sandbox/{session_id}/files/read?path=index.html
    ↓
Returns: { content: "<!DOCTYPE html>..." }
    ↓
Frontend downloads files
    ↓
User has local copy
```

## Multi-Session Support

Your system supports **multiple concurrent sessions**:

```
Session 1 (User A):
  Container: agent-sandbox-aaa111-1779129331
  Workspace: /workspace (isolated)
  Ports: 3000→45001, 5173→45002
  Project: To-Do App

Session 2 (User A):
  Container: agent-sandbox-bbb222-1779129445
  Workspace: /workspace (isolated)
  Ports: 3000→45101, 5173→45102
  Project: Weather App

Session 3 (User B):
  Container: agent-sandbox-ccc333-1779129556
  Workspace: /workspace (isolated)
  Ports: 3000→45201, 5173→45202
  Project: Blog Platform
```

**Key Points:**
- Each session has its own container
- Workspaces are completely isolated
- Ports are dynamically assigned (no conflicts)
- Sessions can run simultaneously
- Max 5 active containers (configurable)

## Folder Structure Inside Container

When agent creates a project, it follows standard conventions:

### Node.js/React Project

```
/workspace/
├── package.json
├── package-lock.json
├── node_modules/
├── public/
│   ├── index.html
│   └── favicon.ico
├── src/
│   ├── index.js
│   ├── App.jsx
│   ├── components/
│   │   ├── Header.jsx
│   │   ├── Footer.jsx
│   │   └── TodoList.jsx
│   ├── styles/
│   │   └── App.css
│   └── utils/
│       └── helpers.js
├── .gitignore
└── README.md
```

### Python/Flask Project

```
/workspace/
├── requirements.txt
├── app.py
├── config.py
├── templates/
│   ├── base.html
│   ├── index.html
│   └── todo.html
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── main.js
├── models/
│   └── todo.py
├── routes/
│   └── api.py
└── README.md
```

### Full-Stack Project

```
/workspace/
├── frontend/
│   ├── package.json
│   ├── src/
│   ├── public/
│   └── node_modules/
├── backend/
│   ├── requirements.txt
│   ├── app.py
│   ├── models/
│   ├── routes/
│   └── venv/
├── docker-compose.yml
└── README.md
```

## How Agent Organizes Files

The agent follows this workflow:

1. **Plan Phase**
   ```json
   {
     "project_name": "todo-app",
     "tech_stack": "React + Node.js",
     "folder_structure": {
       "src": ["App.jsx", "index.js"],
       "public": ["index.html"],
       "components": ["TodoList.jsx", "TodoItem.jsx"]
     }
   }
   ```

2. **Scaffold Phase**
   ```
   Create package.json
   Create folder structure
   Create config files (.gitignore, README.md)
   ```

3. **Implement Phase**
   ```
   Write each file in order:
     1. public/index.html
     2. src/index.js
     3. src/App.jsx
     4. src/components/TodoList.jsx
     5. src/components/TodoItem.jsx
     6. src/styles/App.css
   ```

4. **Execute Phase**
   ```
   npm install
   npm run dev
   ```

## Security & Isolation

### What's Isolated

✅ **Filesystem** - Each container has its own `/workspace`
✅ **Processes** - Processes in one container can't see another
✅ **Network** - Containers have separate IP addresses
✅ **Resources** - CPU and memory limits per container
✅ **Ports** - Dynamic port mapping prevents conflicts

### What's Shared

⚠️ **Docker daemon** - All containers share the same Docker engine
⚠️ **Host network** - Containers can access host network
⚠️ **Host filesystem** - Containers can mount host directories (not used)

### Security Features

1. **No privileged mode** - Containers run as non-root
2. **Resource limits** - Prevents resource exhaustion
3. **Network isolation** - Containers can't access each other
4. **Automatic cleanup** - Old containers are removed
5. **No host mounts** - Containers can't access host files

## Comparison with OpenHands

| Feature | Your System | OpenHands |
|---------|-------------|-----------|
| Container per session | ✅ Yes | ✅ Yes |
| Persistent workspace | ✅ Yes | ✅ Yes |
| Port mapping | ✅ Dynamic | ✅ Dynamic |
| Resource limits | ✅ Yes | ✅ Yes |
| Pause/Resume | ✅ Yes | ✅ Yes |
| Health checks | ✅ Yes | ✅ Yes |
| Auto cleanup | ✅ Yes | ✅ Yes |
| Max containers | ✅ 5 | ✅ 10 |
| Init process | ✅ Yes | ✅ Yes |

## API Endpoints for Workspace Management

### Get Sandbox Status

```bash
GET /api/agent/sandbox/{session_id}/status

Response:
{
  "session_id": "abc-123",
  "container_name": "agent-sandbox-abc123-1779129331",
  "container_ip": "172.17.0.5",
  "status": "running",
  "exposed_ports": [...]
}
```

### List Files in Workspace

```bash
GET /api/agent/sandbox/{session_id}/files

Response:
{
  "files": [
    "package.json",
    "src/App.jsx",
    "src/components/TodoList.jsx",
    "public/index.html"
  ]
}
```

### Read File from Workspace

```bash
GET /api/agent/sandbox/{session_id}/files/read?path=src/App.jsx

Response:
{
  "path": "src/App.jsx",
  "content": "import React from 'react';\n..."
}
```

### Check App Health

```bash
GET /api/agent/sandbox/{session_id}/health?port=3000

Response:
{
  "healthy": true,
  "status_code": 200,
  "url": "http://localhost:45001"
}
```

### Pause Container

```bash
POST /api/agent/sandbox/{session_id}/pause

Response:
{
  "paused": true
}
```

### Resume Container

```bash
POST /api/agent/sandbox/{session_id}/resume

Response:
{
  "resumed": true
}
```

### Delete Container

```bash
DELETE /api/agent/sandbox/{session_id}

Response:
{
  "deleted": true
}
```

## Summary

Your AI Agent Builder creates **isolated Docker containers** for each development session:

✅ **Separate workspace** - Each session has `/workspace` directory
✅ **Isolated terminal** - Persistent bash shell per container
✅ **Dynamic ports** - Auto-assigned host ports for preview
✅ **Resource limits** - 2GB RAM, 50% CPU per container
✅ **Automatic cleanup** - Containers removed after 24 hours
✅ **Multi-session** - Up to 5 concurrent sessions
✅ **Pause/Resume** - Containers can be paused to save resources
✅ **File persistence** - Files persist until container is deleted

This architecture ensures that each user's project is completely isolated and secure, just like OpenHands and GitHub Codespaces.
