# Debugging Guide: Agent Stops Mid-Way

## Current Status

✅ **Backend is running** on port 8001  
✅ **Ollama is working** - tested successfully with qwen2.5-coder:7b  
✅ **Frontend is running** on port 5173  
❌ **WebSocket connection gets stuck** - "listener indicated async response" error

## Root Cause Analysis

The error "A listener indicated an asynchronous response by returning true, but the message channel closed before a response was received" indicates the WebSocket connection is getting stuck during the agent execution.

### Possible Causes:

1. **LLM Response Timeout** - Ollama local models can be slow, causing WebSocket timeout
2. **Database Connection Issue** - PostgreSQL checkpointer might be blocking
3. **Graph Compilation Error** - LangGraph recursion_limit parameter issue
4. **Frontend State Management** - React state not updating properly

## Debugging Steps

### Step 1: Check Backend Logs in Real-Time

Open a new terminal and run:

```bash
cd "/media/aashikant/GAME Volume/aicode/myaiagent/backend"
bash -c 'source venv/bin/activate && PORT=8001 python main.py' 2>&1 | tee backend.log
```

This will show all backend logs including:
- WebSocket connection events
- LangGraph node execution
- Database queries
- LLM API calls
- Error stack traces

### Step 2: Check Browser Console

Open browser DevTools (F12) and check:

1. **Console Tab** - Look for JavaScript errors
2. **Network Tab** - Filter by "WS" to see WebSocket messages
3. **Application Tab** - Check if service workers are interfering

### Step 3: Test Ollama Performance

Run this to see how fast Ollama responds:

```bash
cd "/media/aashikant/GAME Volume/aicode/myaiagent/backend"
bash -c 'source venv/bin/activate && time python debug_ollama.py'
```

If it takes more than 30 seconds, the WebSocket might timeout.

### Step 4: Check Database Connection

```bash
psql -h 127.0.0.1 -p 5433 -U postgres -d aiagent -c "SELECT COUNT(*) FROM checkpoints;"
```

If this hangs, the database is blocking the agent.

### Step 5: Verify WebSocket Connection

Open browser console and run:

```javascript
const ws = new WebSocket('ws://localhost:8001/api/agent/ws');
ws.onopen = () => console.log('Connected');
ws.onerror = (e) => console.error('Error:', e);
ws.onmessage = (e) => console.log('Message:', e.data);
ws.send(JSON.stringify({
  session_id: 'test-123',
  message: 'Hello'
}));
```

This tests if the WebSocket endpoint is working.

## Common Issues and Fixes

### Issue 1: Ollama Model Not Loaded

**Symptom**: Backend logs show "model not found"

**Fix**:
```bash
# Check if model is loaded
ollama list

# If not loaded, pull it
ollama pull qwen2.5-coder:7b

# Verify it's running
curl http://localhost:11434/api/tags
```

### Issue 2: WebSocket Timeout (30 seconds)

**Symptom**: Connection closes after 30 seconds

**Fix**: Increase PING_TIMEOUT in `backend/routes/agent.py`:

```python
PING_TIMEOUT = 120  # Increase from 30 to 120 seconds
```

### Issue 3: LangGraph Recursion Limit

**Symptom**: Backend logs show "recursion limit exceeded"

**Fix**: Already set to 100 in `routes/agent.py`, but verify:

```python
config = {
    "configurable": {"thread_id": session_id},
    "recursion_limit": 100  # Should be here
}
```

### Issue 4: Database Checkpointer Blocking

**Symptom**: Agent hangs at "planning" stage

**Fix**: Disable checkpointer temporarily to test:

In `backend/agent/graph.py`, comment out checkpointer:

```python
# return g.compile(checkpointer=checkpointer, recursion_limit=100)
return g.compile(recursion_limit=100)  # Test without checkpointer
```

### Issue 5: Frontend State Not Updating

**Symptom**: UI shows "connecting" forever

**Fix**: Check `frontend/src/hooks/useAgentStream.ts`:

```typescript
ws.current.onopen = () => {
    console.log('WebSocket opened');  // Add this
    retryCount.current = 0;
    store.setConnectionState('open');
    // ...
};
```

## Recommended Debugging Workflow

1. **Start with backend logs** - This shows exactly where it's stuck
2. **Check browser console** - See if frontend is receiving events
3. **Test Ollama speed** - Slow responses cause timeouts
4. **Verify database** - Checkpointer might be blocking
5. **Test WebSocket directly** - Isolate connection issues

## Quick Fixes to Try Now

### Fix 1: Increase WebSocket Timeout

```bash
cd "/media/aashikant/GAME Volume/aicode/myaiagent/backend"
```

Edit `routes/agent.py` and change:

```python
PING_TIMEOUT = 120  # Was 30
```

### Fix 2: Add More Logging

Edit `backend/agent/nodes.py` and add:

```python
logger.info("node_start", node="plan", session_id=state.get("session_id"))
```

at the start of each node function.

### Fix 3: Test Without Checkpointer

Edit `backend/agent/graph.py`:

```python
# Temporarily disable checkpointer
return g.compile(recursion_limit=100)
```

Restart backend and test.

## Expected Behavior

When working correctly, you should see:

1. **Backend logs**:
   ```
   ws_session_start session_id=xxx
   node_start node=plan
   node_start node=implement
   node_start node=execute
   node_start node=validate
   ```

2. **Browser console**:
   ```
   WebSocket opened
   Event: {type: 'on_chain_start', node: 'plan'}
   Event: {type: 'on_chat_model_stream', chunk: '...'}
   ```

3. **Frontend UI**:
   - Status changes: connecting → planning → implementing → executing
   - Messages appear in chat
   - Files appear in workspace
   - Preview URL becomes available

## Next Steps

1. **Run backend with full logging** (Step 1 above)
2. **Open browser DevTools** and watch console
3. **Send a simple message** like "Create a hello world HTML page"
4. **Watch both logs** to see where it gets stuck
5. **Report back** with the exact error message and last log entry

## Performance Optimization

Once working, optimize Ollama performance:

1. **Use smaller model** for faster responses:
   ```bash
   ollama pull qwen2.5-coder:3b  # Faster than 7b
   ```

2. **Increase Ollama threads**:
   ```bash
   OLLAMA_NUM_THREADS=8 ollama serve
   ```

3. **Use GPU acceleration** if available:
   ```bash
   # Ollama automatically uses GPU if CUDA is available
   nvidia-smi  # Check if GPU is detected
   ```

## Contact Points

If still stuck, provide:

1. Last 50 lines of backend logs
2. Browser console errors
3. Network tab WebSocket messages
4. Exact message you sent to the agent

This will help identify the exact blocking point.
