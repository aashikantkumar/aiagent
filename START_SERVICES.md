# How to Start All Services

## Summary of Issues Fixed

1. ✅ **Session state management** - Files now persist across sessions
2. ✅ **Per-session isolation** - Each session has its own files, logs, and state
3. ✅ **Ollama configuration** - Ready to use with proper setup

## Starting Services

### 1. Start Ollama (Terminal 1)

```bash
# Change to the aicode directory
cd "/media/aashikant/GAME Volume/aicode"

# Set the host binding
export OLLAMA_HOST=0.0.0.0:11434

# Start Ollama
ollama serve
```

Or use the script:
```bash
cd "/media/aashikant/GAME Volume/aicode/myaiagent"
./start_ollama.sh
```

**Keep this terminal open!** Ollama needs to run continuously.

### 2. Pull the Model (Terminal 2)

After Ollama starts, open a new terminal and pull the model:

```bash
# Pull llama3.1:8b
ollama pull llama3.1:8b

# Or pull a faster coding model
ollama pull qwen2.5-coder:7b
```

Wait for the model to download (this may take a few minutes).

### 3. Verify Ollama is Working

```bash
# Check available models
curl http://localhost:11434/api/tags

# Test generation (should respond in a few seconds)
curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "llama3.1:8b", "prompt": "Say hello", "stream": false}' \
  --max-time 10
```

If this times out, your system might be too slow for this model. Try `qwen2.5-coder:7b` instead.

### 4. Start Backend (Terminal 3)

```bash
cd "/media/aashikant/GAME Volume/aicode/myaiagent/backend"

# Activate virtual environment if you have one
source venv/bin/activate  # or source .venv/bin/activate

# Start the backend
python main.py

# Or with uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Keep this terminal open!** The backend needs to run continuously.

### 5. Start Frontend (Terminal 4)

The frontend should already be running. If not:

```bash
cd "/media/aashikant/GAME Volume/aicode/myaiagent/frontend"

# Start the frontend
npm run dev
```

**Keep this terminal open!** The frontend needs to run continuously.

### 6. Open the Application

Open your browser and go to:
```
http://localhost:5173
```

## Configuration Files

### Backend .env

Current configuration (`backend/.env`):
```env
DEBUG=false
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5433
DEFAULT_LLM_PROVIDER=ollama
DEFAULT_LLM_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434
GROQ_API_KEY=gsk_your_actual_key_here
SECRETS_FERNET_KEY=DKT0dPVtqshroIqk_vc5_2PAMuOFbRh7GUrfGOGk5yU=
```

### Alternative: Use Groq (Faster)

If Ollama is too slow, switch to Groq:

1. Edit `backend/.env`:
   ```env
   DEFAULT_LLM_PROVIDER=groq
   DEFAULT_LLM_MODEL=llama-3.3-70b-versatile
   ```

2. Restart the backend

3. No need to run Ollama!

## Troubleshooting

### Ollama Times Out

**Symptom**: Agent takes 10+ minutes or times out

**Solutions**:
1. Use a smaller/faster model: `qwen2.5-coder:7b`
2. Switch to Groq (much faster)
3. Check system resources: `top` or `htop`

### Files Not Showing in Workspace

**Solution**: This is now fixed! Make sure to:
1. Hard refresh browser: `Ctrl+Shift+R` (or `Cmd+Shift+R` on Mac)
2. Check browser console for errors (F12)

### Backend Connection Error

**Symptom**: Frontend shows "WebSocket error. Backend may be offline."

**Solutions**:
1. Check if backend is running: `ps aux | grep "python.*main.py"`
2. Check backend logs for errors
3. Restart backend

### Ollama Not Responding

**Solutions**:
1. Check if Ollama is running: `ps aux | grep ollama`
2. Test Ollama: `curl http://localhost:11434/api/tags`
3. Restart Ollama: `pkill ollama && OLLAMA_HOST=0.0.0.0:11434 ollama serve`

## Quick Start Commands

### Full Restart (All Services)

```bash
# Terminal 1: Ollama
pkill ollama
cd "/media/aashikant/GAME Volume/aicode"
export OLLAMA_HOST=0.0.0.0:11434
ollama serve

# Terminal 2: Backend
cd "/media/aashikant/GAME Volume/aicode/myaiagent/backend"
pkill -f "python.*main.py"
python main.py

# Terminal 3: Frontend (if needed)
cd "/media/aashikant/GAME Volume/aicode/myaiagent/frontend"
npm run dev
```

## Service Status Check

```bash
# Check Ollama
curl http://localhost:11434/api/tags

# Check Backend
curl http://localhost:8000/api/agent/health

# Check Frontend
curl http://localhost:5173
```

## What's Working Now

After the fixes:
- ✅ Files persist across sessions
- ✅ Each session has isolated state
- ✅ Terminal logs are per-session
- ✅ Switching sessions preserves all data
- ✅ Code editor shows generated files
- ✅ File browser shows all files

## Testing the Fix

1. Start all services (Ollama, Backend, Frontend)
2. Open the app in browser
3. Send a message: "Create a simple HTML page with hello world"
4. **You should see**:
   - Files appearing in File Browser (left panel)
   - Code appearing in Monaco Editor (middle panel)
   - Terminal logs in bottom panel
5. Create a new session
6. Generate different files
7. Switch back to first session
8. **Verify**: Original files are still there!

## Performance Tips

### For Faster Development

Use Groq instead of Ollama:
- ✅ 10-100x faster
- ✅ No local resource usage
- ✅ More powerful models
- ✅ Already configured (just change .env)

### For Local Development

Use the fastest Ollama model:
- `qwen2.5-coder:7b` - Best for coding
- `mistral:7b` - Good general model
- Avoid `llama3.1:8b` if your system is slow

## Next Steps

1. Start Ollama in Terminal 1
2. Pull the model in Terminal 2
3. Verify Ollama works
4. Start backend in Terminal 3
5. Open browser to http://localhost:5173
6. Test the agent!

If you encounter any issues, check the troubleshooting section above.
