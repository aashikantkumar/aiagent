# Testing the Session State Fix

## Quick Test Guide

Follow these steps to verify the session state management fix is working correctly:

### Test 1: File Persistence Across Sessions

1. **Create Session 1**:
   - Open the app in your browser (http://localhost:5173)
   - Send a message: "Create a simple HTML page with a hello world message"
   - Wait for the agent to generate files
   - Note the files shown in the File Browser (left panel)
   - Note the code shown in the Code Editor (middle panel)

2. **Create Session 2**:
   - Click "New app" button in the sidebar
   - Send a different message: "Create a Python script that prints numbers 1-10"
   - Wait for the agent to generate files
   - Note the NEW files shown (should be different from Session 1)

3. **Switch Back to Session 1**:
   - Click on the first session in the sidebar
   - ✅ **VERIFY**: The HTML files from Session 1 should reappear
   - ✅ **VERIFY**: The code editor should show the HTML content
   - ✅ **VERIFY**: The file browser should show the HTML files

4. **Switch to Session 2 Again**:
   - Click on the second session
   - ✅ **VERIFY**: The Python files should reappear
   - ✅ **VERIFY**: The code editor should show the Python content

### Test 2: Terminal Logs Isolation

1. **In Session 1**:
   - Note any terminal output in the bottom panel
   - Look for execution logs, sandbox messages, etc.

2. **Switch to Session 2**:
   - ✅ **VERIFY**: Terminal should clear and show different logs
   - ✅ **VERIFY**: Logs should be specific to Session 2's execution

3. **Switch Back to Session 1**:
   - ✅ **VERIFY**: Original Session 1 logs should reappear
   - ✅ **VERIFY**: No Session 2 logs should be visible

### Test 3: Code Execution Independence

1. **In Session 1** (HTML app):
   - Wait for the browser preview to load (right panel)
   - ✅ **VERIFY**: Preview shows the HTML page

2. **In Session 2** (Python script):
   - Check terminal for Python execution output
   - ✅ **VERIFY**: Terminal shows Python output

3. **Switch Between Sessions**:
   - ✅ **VERIFY**: Each session maintains its own preview/execution state
   - ✅ **VERIFY**: No cross-contamination between sessions

### Test 4: Active File Selection

1. **In Session 1**:
   - Click on a specific file in the File Browser
   - Note which file is highlighted and shown in the editor

2. **Switch to Session 2**:
   - ✅ **VERIFY**: A different file is active (or no file if none selected)

3. **Switch Back to Session 1**:
   - ✅ **VERIFY**: The same file you selected is still active
   - ✅ **VERIFY**: The editor shows the correct file content

### Test 5: Multiple Sessions Simultaneously

1. **Create 3-4 different sessions** with different apps:
   - Session 1: HTML/CSS website
   - Session 2: Python script
   - Session 3: React app
   - Session 4: Node.js server

2. **Rapidly switch between them**:
   - ✅ **VERIFY**: Each session shows its own files
   - ✅ **VERIFY**: Each session shows its own logs
   - ✅ **VERIFY**: No data loss or mixing between sessions

### Test 6: Browser Refresh Persistence

1. **Create a session with files**
2. **Refresh the browser** (F5 or Ctrl+R)
3. ✅ **VERIFY**: Session list is preserved (stored in localStorage)
4. ✅ **VERIFY**: Active session is remembered
5. ⚠️ **NOTE**: Files and logs are NOT persisted to backend yet, so they will be lost on refresh
   - This is expected behavior - only session metadata persists

## Expected Behavior Summary

### ✅ What Should Work Now

- **Session Isolation**: Each session has its own files, logs, and state
- **Session Switching**: Switching sessions preserves all data
- **Multiple Sessions**: Can work on multiple apps simultaneously
- **Terminal Logs**: Each session has independent terminal output
- **File Selection**: Active file is remembered per session
- **Browser Preview**: Each session can have its own preview URL

### ⚠️ Known Limitations

- **No Backend Persistence**: Files and logs are only stored in browser memory
  - Refreshing the browser will lose file content (but session list persists)
  - To add backend persistence, implement session state storage in PostgreSQL

- **WebSocket Connection**: Only one WebSocket connection at a time
  - Switching sessions closes the previous connection
  - This is by design to avoid multiple concurrent agent executions

## Troubleshooting

### Issue: Files Still Disappearing

**Check**:
1. Open browser DevTools (F12)
2. Go to Console tab
3. Look for any errors related to Zustand or state management
4. Check if the frontend dev server reloaded the changes

**Solution**:
- Hard refresh: Ctrl+Shift+R (or Cmd+Shift+R on Mac)
- Clear browser cache and reload
- Restart the frontend dev server: `cd frontend && npm run dev`

### Issue: Terminal Shows Mixed Logs

**Check**:
1. Verify the Terminal component is using `activeSessionId`
2. Check browser console for errors

**Solution**:
- The Terminal component should clear and reload when session changes
- If not, try switching sessions a few times to trigger the effect

### Issue: TypeScript Errors

**Check**:
1. Run `npm run build` in the frontend directory
2. Look for type errors

**Solution**:
- The computed getters in the store should satisfy TypeScript
- If errors persist, check that all components are using the store correctly

## Debugging Tips

### View Store State

Add this to your browser console to inspect the store:

```javascript
// Get the store state
const state = window.__ZUSTAND_STORE_STATE__;

// Or access via React DevTools
// Install React DevTools extension
// Look for "Zustand" in the components tree
```

### Monitor Session Changes

Add console logs to track session switching:

```typescript
// In agentStore.ts, add to setActiveSession:
console.log('Switching to session:', id);
console.log('Files for this session:', get().filesBySession[id]);
console.log('Logs for this session:', get().logsBySession[id]);
```

### Check WebSocket Events

Monitor WebSocket messages in browser DevTools:
1. Open DevTools (F12)
2. Go to Network tab
3. Filter by "WS" (WebSocket)
4. Click on the WebSocket connection
5. View Messages tab to see all events

## Success Criteria

The fix is working correctly if:

- ✅ You can create multiple sessions
- ✅ Each session shows different files
- ✅ Switching sessions preserves all data
- ✅ Terminal logs are isolated per session
- ✅ No errors in browser console
- ✅ Code execution works independently in each session

## Next Steps

If all tests pass, consider:

1. **Add Backend Persistence**: Store session files in PostgreSQL
2. **Add Session Export**: Allow users to download session data
3. **Add Session Sharing**: Share sessions between users
4. **Add Session History**: Track changes over time
5. **Add Session Search**: Find sessions by content or tags
