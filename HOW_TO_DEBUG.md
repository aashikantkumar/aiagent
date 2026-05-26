# How to Debug: Agent Stops Mid-Way

## Quick Summary

**Your Issue**: Agent gets stuck with error "A listener indicated an asynchronous response by returning true, but the message channel closed before a response was received"

**Root Cause**: WebSocket timeout (30 seconds) is too short for Ollama's slower response times

**Fix Applied**: ✅ Increased PING_TIMEOUT from 30 to 120 seconds in `backend/routes/agent.py`

**Status**: 
- ✅ Backend running (port 8001)
- ✅ Ollama working (qwen2.5-coder:7b)
- ✅ Frontend running (port 5173)
- ⚠️ Need to restart backend to apply fix

## Step-by-Step Debugging

### Step 1: Restart Backend with Logging

**Option A: Using the debug script (Recommended)**

```bash
cd "/media/aashikant/GAME Volume/aicode/myaiagent"
./start_debug.sh
```

This will:
- Check if Ollama is running
- Check if PostgreSQL is running
- Kill any existing backend process
- Start backend with full logging
- Save logs to `backend.log`

**Option B: Manual restart**

```bash
# Kill existing backend
pkill -f "python main.py"

# Start with logging
cd "/media/aashikant/GAME Volume/aicode/myaiagent/backend"
bash -c 'source venv/bin/activate && PORT=8001 python main.py 2>&1 | tee backend.log'
```

### Step 2: Open Browser DevTools

1. Open your application: http://localhost:5173
2. Press F12 to open DevTools
3. Go to **Console** tab
4. Clear any existing logs

### Step 3: Send a Test Message

Send a simple message to test:

```
Create a simple hello.html file with a greeting
```

### Step 4: Watch the Logs

**In the backend terminal**, you should see:

```
ws_session_start session_id=xxx
checkpointer_init backend=postgres
[LangGraph events streaming...]
```

**In the browser console**, you should see:

```
WebSocket opened
Event: {type: 'on_chain_start', node: 'plan'}
Event: {type: 'on_chat_model_stream', chunk: '...'}
```

### Step 5: Identify Where It Gets Stuck

If it stops, note the **last log entry** in both places:

- **Backend**: Last node that executed
- **Browser**: Last event received

Common stuck points:

1. **"planning"** - LLM is taking too long to respond
2. **"implementing"** - Code generation is slow
3. **"executing"** - Command execution failed
4. **"validating"** - App didn't start

## Using the WebSocket Test Tool

For more detailed debugging, use the test tool:

```bash
# Open in browser
firefox "/media/aashikant/GAME Volume/aicode/myaiagent/test_websocket.html"
```

This shows:
- Exact WebSocket messages
- Ping/pong heartbeats
- Connection status
- All events in real-time

## Common Issues and Solutions

### Issue 1: Still Times Out After 120 Seconds

**Cause**: Ollama is very slow (7B model on CPU)

**Solutions**:

A. Use a smaller model (faster):
```bash
ollama pull qwen2.5-coder:3b
```

Then update `.env`:
```env
DEFAULT_LLM_MODEL=qwen2.5-coder:3b
```

B. Increase timeout even more:
```python
# In backend/routes/agent.py
PING_TIMEOUT = 300  # 5 minutes
```

C. Use GPU acceleration (if available):
```bash
nvidia-smi  # Check if GPU is detected
# Ollama automatically uses GPU if available
```

### Issue 2: Database Checkpointer Slow

**Symptom**: Hangs at "planning" stage

**Fix**: Disable checkpointer temporarily:

```python
# In backend/agent/graph.py, line 102
return g.compile()  # Remove checkpointer parameter
```

Restart backend and test.

### Issue 3: Frontend Not Updating

**Symptom**: Backend logs show progress, but UI stuck

**Fix**: Check browser console for React errors

Common causes:
- State management issue
- WebSocket not receiving messages
- React component not re-rendering

### Issue 4: Ollama Not Responding

**Test Ollama directly**:

```bash
cd "/media/aashikant/GAME Volume/aicode/myaiagent/backend"
bash -c 'source venv/bin/activate && python debug_ollama.py'
```

If this fails:
```bash
# Restart Ollama
pkill ollama
ollama serve
```

## Performance Tips

### 1. Optimize Ollama

```bash
# Use more CPU threads
OLLAMA_NUM_THREADS=8 ollama serve

# Use GPU if available (automatic)
nvidia-smi
```

### 2. Reduce Token Usage

Edit `backend/agent/prompts.py` to make prompts shorter:

```python
# Shorter system prompt = faster responses
SYSTEM_PROMPT = """You are a code generator. Be concise."""
```

### 3. Increase Batch Size

Edit `backend/agent/nodes.py`:

```python
# Generate multiple files at once instead of one-by-one
# This reduces the number of LLM calls
```

## Expected Performance

### With qwen2.5-coder:7b (CPU)

- **Simple HTML file**: 10-20 seconds
- **React component**: 30-60 seconds
- **Full application (5 files)**: 3-5 minutes
- **Complex SRS (20 files)**: 10-15 minutes

### With qwen2.5-coder:3b (CPU)

- **Simple HTML file**: 5-10 seconds
- **React component**: 15-30 seconds
- **Full application (5 files)**: 2-3 minutes
- **Complex SRS (20 files)**: 5-8 minutes

### With Groq (Cloud API)

- **Any task**: 1-2 seconds per response
- **Limitation**: Rate limited to 12K tokens/min
- **Result**: Stops mid-way on large applications

## What to Report If Still Stuck

If the issue persists, provide:

### 1. Backend Logs (Last 50 Lines)

```bash
tail -50 "/media/aashikant/GAME Volume/aicode/myaiagent/backend/backend.log"
```

### 2. Browser Console Errors

- Open DevTools (F12)
- Console tab
- Copy all red errors

### 3. WebSocket Messages

- DevTools → Network tab
- Filter: WS
- Click on the WebSocket connection
- Messages tab
- Copy last 10 messages

### 4. Test Details

- What message did you send?
- How long did it run before getting stuck?
- What was the last status shown in UI?
- Did you see any files generated?

## Files Created for Debugging

1. **DEBUGGING_GUIDE.md** - Comprehensive debugging guide
2. **CURRENT_STATUS.md** - System status and analysis
3. **HOW_TO_DEBUG.md** - This file (step-by-step instructions)
4. **test_websocket.html** - Interactive WebSocket testing tool
5. **debug_ollama.py** - Direct Ollama connection test
6. **start_debug.sh** - Automated debug startup script

## Quick Commands Reference

```bash
# Restart backend with logging
./start_debug.sh

# Test Ollama
cd backend && bash -c 'source venv/bin/activate && python debug_ollama.py'

# Check backend status
curl http://localhost:8001/

# Check Ollama status
curl http://localhost:11434/api/tags

# View backend logs
tail -f backend/backend.log

# Kill backend
pkill -f "python main.py"

# Check what's using port 8001
lsof -i :8001
```

## Next Steps

1. **Restart backend** using `./start_debug.sh`
2. **Open browser** to http://localhost:5173
3. **Send a simple message** like "Create hello.html"
4. **Watch both logs** (backend terminal + browser console)
5. **Report back** with results

The timeout fix should resolve the issue. If not, we'll investigate further based on the logs.
