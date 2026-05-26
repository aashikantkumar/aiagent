# Quick Start: Ollama Setup

## Start Ollama (Copy & Paste)

Open a new terminal and run:

```bash
cd "/media/aashikant/GAME Volume/aicode" && export OLLAMA_HOST=0.0.0.0:11434 && ollama serve
```

**Keep this terminal open!**

## Pull Model (One-Time Setup)

In another terminal:

```bash
ollama pull llama3.1:8b
```

Wait for download to complete (may take a few minutes).

## Verify Ollama is Working

```bash
# Check models
curl http://localhost:11434/api/tags

# Test generation
curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "llama3.1:8b", "prompt": "Hello", "stream": false}' \
  --max-time 10
```

Should respond in a few seconds. If it times out, your system may be too slow.

## Alternative: Use Groq (Faster)

If Ollama is too slow, edit `backend/.env`:

```env
DEFAULT_LLM_PROVIDER=groq
DEFAULT_LLM_MODEL=llama-3.3-70b-versatile
```

Then restart backend. No need to run Ollama!

## Restart Backend

After changing `.env`:

```bash
cd "/media/aashikant/GAME Volume/aicode/myaiagent/backend"
# Kill existing backend
pkill -f "python.*main.py"
# Start again
python main.py
```

## Test the Application

1. Open browser: http://localhost:5173
2. Send message: "Create a simple HTML page"
3. Watch files appear in workspace!

## Troubleshooting

### Ollama Times Out
- Use Groq instead (much faster)
- Or try smaller model: `ollama pull qwen2.5-coder:7b`

### Files Not Showing
- Hard refresh browser: Ctrl+Shift+R
- Check browser console (F12) for errors

### Backend Error
- Check if backend is running: `ps aux | grep "python.*main.py"`
- Check backend logs for errors
- Restart backend

## Summary

✅ Session state fix applied - files persist across sessions
✅ Workspace display fixed - files appear in editor
✅ Ollama configuration ready

Just start Ollama and test!
