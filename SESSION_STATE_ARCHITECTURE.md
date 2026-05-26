# Session State Architecture

## Visual Overview

### Before: Global State (Broken)

```
┌─────────────────────────────────────────────────────────────┐
│                      Zustand Store                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Global State (Shared by All Sessions)              │   │
│  │                                                      │   │
│  │  files: { "index.html": "...", "app.js": "..." }   │   │
│  │  logs: "Building app...\nRunning tests..."         │   │
│  │  activeFile: "index.html"                           │   │
│  │  sandbox: { container_id: "abc123" }                │   │
│  │  previewUrl: "http://localhost:3000"                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Sessions:                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │Session 1 │  │Session 2 │  │Session 3 │                 │
│  │(HTML App)│  │(Python)  │  │(React)   │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
│       ↓              ↓              ↓                       │
│       └──────────────┴──────────────┘                       │
│                      │                                      │
│              All share same state!                          │
│              Switching sessions = data loss!                │
└─────────────────────────────────────────────────────────────┘

Problem: When switching from Session 1 to Session 2,
         Session 1's files are cleared and lost!
```

### After: Per-Session State (Fixed)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Zustand Store                                 │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │  Per-Session State (Isolated by Session ID)                   │     │
│  │                                                                │     │
│  │  filesBySession: {                                             │     │
│  │    "session-1": { "index.html": "...", "app.js": "..." }     │     │
│  │    "session-2": { "main.py": "...", "utils.py": "..." }      │     │
│  │    "session-3": { "App.tsx": "...", "index.tsx": "..." }     │     │
│  │  }                                                             │     │
│  │                                                                │     │
│  │  logsBySession: {                                              │     │
│  │    "session-1": "Building HTML app...\n"                      │     │
│  │    "session-2": "Running Python script...\n"                  │     │
│  │    "session-3": "Starting React dev server...\n"              │     │
│  │  }                                                             │     │
│  │                                                                │     │
│  │  activeFileBySession: {                                        │     │
│  │    "session-1": "index.html"                                  │     │
│  │    "session-2": "main.py"                                     │     │
│  │    "session-3": "App.tsx"                                     │     │
│  │  }                                                             │     │
│  │                                                                │     │
│  │  sandboxBySession: { ... }                                     │     │
│  │  previewUrlBySession: { ... }                                  │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                                                                         │
│  Active Session: "session-2"                                            │
│                                                                         │
│  Computed Getters (Auto-select active session data):                   │
│  ┌───────────────────────────────────────────────────────────────┐     │
│  │  get files() → filesBySession["session-2"]                    │     │
│  │  get logs() → logsBySession["session-2"]                      │     │
│  │  get activeFile() → activeFileBySession["session-2"]          │     │
│  │  get sandbox() → sandboxBySession["session-2"]                │     │
│  │  get previewUrl() → previewUrlBySession["session-2"]          │     │
│  └───────────────────────────────────────────────────────────────┘     │
│                                                                         │
│  Sessions:                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                             │
│  │Session 1 │  │Session 2 │  │Session 3 │                             │
│  │(HTML App)│  │(Python)  │  │(React)   │                             │
│  └──────────┘  └────┬─────┘  └──────────┘                             │
│                     │                                                   │
│                  Active!                                                │
│                                                                         │
│  ✅ Each session has isolated state                                     │
│  ✅ Switching sessions preserves all data                               │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Session Creation

```
User clicks "New app"
        ↓
createNewSession()
        ↓
Generate unique session ID
        ↓
Add to sessions array
        ↓
Set as activeSessionId
        ↓
Initialize empty state for this session:
  - filesBySession[newId] = {}
  - logsBySession[newId] = ""
  - activeFileBySession[newId] = null
  - sandboxBySession[newId] = null
  - previewUrlBySession[newId] = null
```

### Session Switching

```
User clicks on Session 2
        ↓
setActiveSession("session-2")
        ↓
Update activeSessionId = "session-2"
        ↓
Computed getters automatically return Session 2 data:
  - files → filesBySession["session-2"]
  - logs → logsBySession["session-2"]
  - activeFile → activeFileBySession["session-2"]
        ↓
Components re-render with Session 2 data
        ↓
✅ Session 1 data is preserved in filesBySession["session-1"]
```

### File Generation

```
Agent generates file "index.html"
        ↓
WebSocket event received
        ↓
handleAgentContent(content, sessionId)
        ↓
Extract file path and content
        ↓
setFile("index.html", content, sessionId)
        ↓
Update filesBySession[sessionId]["index.html"] = content
        ↓
Components re-render showing new file
```

### Terminal Logging

```
Agent executes command
        ↓
WebSocket event with output
        ↓
addLog(output, sessionId)
        ↓
Append to logsBySession[sessionId]
        ↓
Terminal component detects change
        ↓
If session changed:
  - Clear terminal
  - Write all logs for new session
Else:
  - Append new logs only
```

## Component Integration

### How Components Access Session Data

```typescript
// In any component:
import { useAgentStore } from '../store/agentStore';

function MyComponent() {
    // These automatically get data for the active session
    const { files, logs, activeFile, sandbox } = useAgentStore();
    
    // files = filesBySession[activeSessionId]
    // logs = logsBySession[activeSessionId]
    // etc.
    
    return (
        <div>
            {Object.keys(files).map(path => (
                <div key={path}>{path}</div>
            ))}
        </div>
    );
}
```

### How WebSocket Hook Updates Session Data

```typescript
// In useAgentStream.ts:
const handleEvent = (event, sessionId) => {
    const store = useAgentStore.getState();
    
    // Always pass sessionId to ensure correct session is updated
    store.addLog(`Processing ${event.type}`, sessionId);
    store.setFile(path, content, sessionId);
    store.setSandbox(sandboxInfo, sessionId);
};
```

## State Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Lifecycle                     │
└─────────────────────────────────────────────────────────────┘

1. App Loads
   ↓
   Load sessions from localStorage
   ↓
   Initialize store with empty per-session state
   ↓
   Set activeSessionId from localStorage

2. User Creates Session
   ↓
   Generate new session ID
   ↓
   Add to sessions array
   ↓
   Initialize empty state for this session
   ↓
   Persist sessions to localStorage

3. User Sends Message
   ↓
   Open WebSocket connection
   ↓
   Send message with session_id
   ↓
   Receive events from backend
   ↓
   Update per-session state (files, logs, etc.)

4. User Switches Session
   ↓
   Update activeSessionId
   ↓
   Computed getters return new session's data
   ↓
   Components re-render with new data
   ↓
   Terminal clears and shows new session's logs

5. User Refreshes Browser
   ↓
   Sessions list persists (localStorage)
   ↓
   Active session ID persists (localStorage)
   ↓
   ⚠️ Files and logs are lost (not persisted to backend)
   ↓
   User can resume session but needs to regenerate files
```

## Memory Management

### Current Approach (In-Memory Only)

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser Memory                            │
│                                                              │
│  Zustand Store                                               │
│  ├── Session 1 State (files, logs, sandbox)                 │
│  ├── Session 2 State (files, logs, sandbox)                 │
│  ├── Session 3 State (files, logs, sandbox)                 │
│  └── ...                                                     │
│                                                              │
│  ⚠️ All data lost on browser refresh                         │
│  ⚠️ Memory usage grows with number of sessions               │
└─────────────────────────────────────────────────────────────┘
```

### Future Approach (Backend Persistence)

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser Memory                            │
│                                                              │
│  Zustand Store (Active Session Only)                        │
│  └── Current Session State                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                        ↕
                   API Calls
                        ↕
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                       │
│                                                              │
│  session_files table                                         │
│  ├── session_id | file_path | content | updated_at          │
│  ├── session-1  | index.html | ...    | 2024-01-01          │
│  ├── session-1  | app.js     | ...    | 2024-01-01          │
│  ├── session-2  | main.py    | ...    | 2024-01-01          │
│  └── ...                                                     │
│                                                              │
│  session_logs table                                          │
│  ├── session_id | log_entry | timestamp                     │
│  └── ...                                                     │
│                                                              │
│  ✅ Data persists across browser refreshes                   │
│  ✅ Lower memory usage in browser                            │
│  ✅ Can sync across devices                                  │
└─────────────────────────────────────────────────────────────┘
```

## Performance Considerations

### Current Implementation

- **Memory Usage**: O(n × m) where n = sessions, m = avg files per session
- **Switching Speed**: O(1) - just updates activeSessionId
- **Rendering**: Only active session's data is rendered
- **Garbage Collection**: Old session data stays in memory until page refresh

### Optimization Opportunities

1. **Lazy Loading**: Only load session data when switching to it
2. **LRU Cache**: Keep only N most recent sessions in memory
3. **Compression**: Compress file content for inactive sessions
4. **Backend Sync**: Offload old sessions to backend storage
5. **Virtual Scrolling**: For sessions with many files

## Testing Strategy

### Unit Tests

```typescript
describe('agentStore', () => {
    it('should isolate files by session', () => {
        const store = useAgentStore.getState();
        
        store.setFile('file1.txt', 'content1', 'session-1');
        store.setFile('file2.txt', 'content2', 'session-2');
        
        store.setActiveSession('session-1');
        expect(store.files).toEqual({ 'file1.txt': 'content1' });
        
        store.setActiveSession('session-2');
        expect(store.files).toEqual({ 'file2.txt': 'content2' });
    });
    
    it('should isolate logs by session', () => {
        const store = useAgentStore.getState();
        
        store.addLog('log1', 'session-1');
        store.addLog('log2', 'session-2');
        
        store.setActiveSession('session-1');
        expect(store.logs).toContain('log1');
        expect(store.logs).not.toContain('log2');
    });
});
```

### Integration Tests

```typescript
describe('Session Switching', () => {
    it('should preserve files when switching sessions', async () => {
        // Create session 1 and generate files
        await createSession();
        await generateFiles(['index.html', 'app.js']);
        
        // Create session 2 and generate different files
        await createSession();
        await generateFiles(['main.py']);
        
        // Switch back to session 1
        await switchToSession(1);
        
        // Verify session 1 files are still there
        expect(getVisibleFiles()).toEqual(['index.html', 'app.js']);
    });
});
```

## Migration Path

If you need to add backend persistence later:

1. **Add Database Tables**:
   ```sql
   CREATE TABLE session_files (
       id SERIAL PRIMARY KEY,
       session_id VARCHAR(255) NOT NULL,
       file_path TEXT NOT NULL,
       content TEXT NOT NULL,
       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       UNIQUE(session_id, file_path)
   );
   
   CREATE TABLE session_logs (
       id SERIAL PRIMARY KEY,
       session_id VARCHAR(255) NOT NULL,
       log_entry TEXT NOT NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

2. **Add API Endpoints**:
   ```python
   @router.get("/sessions/{session_id}/files")
   async def get_session_files(session_id: str):
       # Return all files for this session
       
   @router.post("/sessions/{session_id}/files")
   async def save_session_file(session_id: str, file: FileCreate):
       # Save file to database
   ```

3. **Update Store to Sync**:
   ```typescript
   setFile: async (path, content, sessionId) => {
       // Update local state
       set((state) => ({
           filesBySession: {
               ...state.filesBySession,
               [sessionId]: {
                   ...state.filesBySession[sessionId],
                   [path]: content
               }
           }
       }));
       
       // Sync to backend
       await api.sessions.saveFile(sessionId, path, content);
   }
   ```

This architecture provides a solid foundation for session management while keeping the door open for future enhancements!
