# Session State Management Fix

## Problem Summary

The Antigravity Agent Builder had three critical issues with session management:

1. **Files/Code not persisting across sessions**: When switching between sessions, all generated files and code disappeared
2. **Terminal showing same output for all sessions**: All sessions shared the same terminal logs
3. **Code execution issues**: Files were not properly isolated per session, causing execution problems

## Root Cause

The Zustand store (`agentStore.ts`) was storing session-specific data (files, logs, sandbox info) as **global state** instead of **per-session state**. When switching sessions, the store would clear all this data, losing the context of previous sessions.

### Before (Problematic Code)

```typescript
interface AgentStore {
    // ... other fields
    files: Record<string, string>;        // ❌ Global
    activeFile: string | null;            // ❌ Global
    logs: string;                         // ❌ Global
    sandbox: SandboxInfo | null;          // ❌ Global
    previewUrl: string | null;            // ❌ Global
}

setActiveSession: (id) => set((state) => {
    return {
        activeSessionId: id,
        files: {},              // ❌ Clears all files!
        activeFile: null,       // ❌ Clears active file!
        logs: '',               // ❌ Clears all logs!
        sandbox: null,          // ❌ Clears sandbox!
        previewUrl: null,       // ❌ Clears preview!
    };
}),
```

## Solution

Refactored the store to maintain **per-session state** using Record types keyed by session ID:

### After (Fixed Code)

```typescript
interface AgentStore {
    // Per-session state (stored by session ID)
    filesBySession: Record<string, Record<string, string>>;
    activeFileBySession: Record<string, string | null>;
    logsBySession: Record<string, string>;
    sandboxBySession: Record<string, SandboxInfo | null>;
    previewUrlBySession: Record<string, string | null>;

    // Computed getters for current session
    files: Record<string, string>;
    activeFile: string | null;
    logs: string;
    sandbox: SandboxInfo | null;
    previewUrl: string | null;
}

// Computed getters automatically return data for active session
get files() {
    return get().filesBySession[get().activeSessionId] || {};
},

setActiveSession: (id) => set((state) => {
    return {
        activeSessionId: id,  // ✅ Only changes active session
        // All session data is preserved!
    };
}),
```

## Changes Made

### 1. Store Structure (`agentStore.ts`)

- **Added per-session storage**:
  - `filesBySession: Record<string, Record<string, string>>`
  - `activeFileBySession: Record<string, string | null>`
  - `logsBySession: Record<string, string>`
  - `sandboxBySession: Record<string, SandboxInfo | null>`
  - `previewUrlBySession: Record<string, string | null>`

- **Added computed getters** that automatically return data for the active session:
  - `get files()` → returns `filesBySession[activeSessionId]`
  - `get activeFile()` → returns `activeFileBySession[activeSessionId]`
  - `get logs()` → returns `logsBySession[activeSessionId]`
  - `get sandbox()` → returns `sandboxBySession[activeSessionId]`
  - `get previewUrl()` → returns `previewUrlBySession[activeSessionId]`

- **Updated all setter methods** to accept optional `sessionId` parameter:
  - `setFile(path, content, sessionId?)`
  - `replaceFiles(files, sessionId?)`
  - `setActiveFile(activeFile, sessionId?)`
  - `addLog(log, sessionId?)`
  - `setSandbox(sandbox, sessionId?)`
  - `setPreviewUrl(url, sessionId?)`

### 2. WebSocket Hook (`useAgentStream.ts`)

Updated all store method calls to pass the `sessionId`:

```typescript
// Before
store.addLog(`> Could not read ${path}`);
store.setSandbox(sandbox);
store.replaceFiles(files);

// After
store.addLog(`> Could not read ${path}`, sessionId);
store.setSandbox(sandbox, sessionId);
store.replaceFiles(files, sessionId);
```

### 3. Terminal Component (`Terminal.tsx`)

Added session change detection to properly reset and restore terminal content:

```typescript
// Reset terminal when session changes
useEffect(() => {
    if (lastSessionId.current !== activeSessionId) {
        if (xtermRef.current) {
            xtermRef.current.clear();
            xtermRef.current.writeln('\x1b[35m[Sandbox Environment Initialized]\x1b[0m');
            lastLogsLength.current = 0;
            
            // Write all logs for the new session
            if (logs) {
                xtermRef.current.write(logs);
                lastLogsLength.current = logs.length;
            }
        }
        lastSessionId.current = activeSessionId;
    }
}, [activeSessionId, logs]);
```

## Benefits

### ✅ Session Isolation
Each session now maintains its own:
- Generated files and code
- Terminal logs
- Sandbox container info
- Browser preview URL
- Active file selection

### ✅ Seamless Session Switching
Users can now:
- Switch between sessions without losing work
- See different files and logs for each session
- Run multiple apps simultaneously in different sessions
- Resume work on any session at any time

### ✅ Backward Compatibility
- All existing components continue to work without changes
- The computed getters provide the same interface as before
- Components access `files`, `logs`, etc. as before, but now get session-specific data

## Testing Checklist

To verify the fix works:

1. ✅ Create a new session and generate some files
2. ✅ Create another session and generate different files
3. ✅ Switch back to the first session
4. ✅ Verify the original files are still there
5. ✅ Check that terminal logs are different for each session
6. ✅ Verify code execution works in each session independently
7. ✅ Test browser preview shows correct app for each session

## Migration Notes

**No migration required!** The changes are backward compatible. Existing sessions in localStorage will continue to work, and new per-session data will be created as users interact with the application.

## Files Modified

1. `/frontend/src/store/agentStore.ts` - Core state management
2. `/frontend/src/hooks/useAgentStream.ts` - WebSocket event handling
3. `/frontend/src/components/Terminal.tsx` - Terminal display logic

## Future Improvements

Consider adding:
- Session data persistence to backend database
- Session export/import functionality
- Session cloning/duplication
- Session search and filtering
- Session tags and categories
