# Ollama Troubleshooting Guide

## Current Issue

Your Ollama service is running but timing out on requests. The error shows:
```
litellm.Timeout: Connection timed out. Timeout passed=600.0, time taken=600.004 seconds
```

This means the model took over 10 minutes to respond, which is too slow.

## Diagnosis

From the process list, I can see:
- Ollama server is running (PID 22206)
- A model runner is active and using 308% CPU and 31% RAM (5GB)
- The model appears to be stuck or processing a very long request

## Solutions

### Option 1: Restart Ollama (Recommended)

The model might be stuck on a previous request. Restart it:

```bash
# Kill the Ollama process
pkill ollama

# Wait a few seconds
sleep 3

# Start Ollama again
ollama serve &

# Wait for it to start
sleep 5

# Test it
curl http://localhost:11434/api/tags
```

### Option 2: Use a Faster Model

The `llama3.1:8b` model might be too large for your hardware. Try a smaller model:

```bash
# Pull a smaller, faster model
ollama pull qwen2.5-coder:7b

# Update your .env file
DEFAULT_LLM_MODEL=qwen2.5-coder:7b
```

You already have `qwen2.5-coder:7b` installed, which is optimized for coding tasks!

### Option 3: Use Groq Instead (Fastest)

Groq is much faster than local Ollama. You already have a Groq API key configured:

```bash
# Update .env file
DEFAULT_LLM_PROVIDER=groq
DEFAULT_LLM_MODEL=llama-3.3-70b-versatile
```

Groq advantages:
- ✅ Much faster (seconds vs minutes)
- ✅ No local GPU/CPU usage
- ✅ More powerful models
- ✅ No setup required

### Option 4: Reduce Timeout

If you want to keep using Ollama but avoid long waits, reduce the timeout in the backend code.

## Quick Fix Steps

### Step 1: Restart Ollama

```bash
# In a terminal:
pkill ollama
sleep 3
ollama serve
```

### Step 2: Test Ollama

```bash
# In another terminal:
curl -X POST http://localhost:11434/api/generate \
  -d '{"model": "llama3.1:8b", "prompt": "Hello", "stream": false}' \
  --max-time 10
```

If this times out, Ollama is too slow for your hardware.

### Step 3: Switch to Faster Model

```bash
# Update backend/.env
DEFAULT_LLM_MODEL=qwen2.5-coder:7b
```

Then restart your backend server.

### Step 4: If Still Slow, Use Groq

```bash
# Update backend/.env
DEFAULT_LLM_PROVIDER=groq
DEFAULT_LLM_MODEL=llama-3.3-70b-versatile
```

Then restart your backend server.

## Restart Backend Server

After making changes to `.env`, restart the backend:

```bash
# Find the backend process
ps aux | grep "python.*main.py" | grep -v grep

# Kill it (replace PID with actual process ID)
kill <PID>

# Or use pkill
pkill -f "python.*main.py"

# Start it again
cd /media/aashikant/GAME\ Volume/aicode/myaiagent/backend
python main.py
```

Or if using uvicorn:
```bash
pkill -f uvicorn
cd /media/aashikant/GAME\ Volume/aicode/myaiagent/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Recommended Configuration

For best performance with your setup:

### For Local Development (Ollama)
```env
DEFAULT_LLM_PROVIDER=ollama
DEFAULT_LLM_MODEL=qwen2.5-coder:7b  # Faster than llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434
```

### For Production/Fast Development (Groq)
```env
DEFAULT_LLM_PROVIDER=groq
DEFAULT_LLM_MODEL=llama-3.3-70b-versatile
GROQ_API_KEY=gsk_your_actual_key_here
```

## Checking System Resources

Check if your system has enough resources for Ollama:

```bash
# Check CPU usage
top -bn1 | head -20

# Check memory
free -h

# Check if GPU is available (if you have one)
nvidia-smi  # For NVIDIA GPUs
```

If CPU is maxed out or memory is low, Ollama will be very slow.

## Model Comparison

| Model | Size | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| qwen2.5-coder:7b | 4.7GB | Fast | Good | Coding tasks |
| llama3.1:8b | 4.9GB | Slow | Better | General tasks |
| mistral:7b | 4.4GB | Medium | Good | General tasks |
| groq/llama-3.3-70b | Cloud | Very Fast | Excellent | Everything |

## Current Status

Based on the logs:
- ✅ Ollama is installed and running
- ✅ Models are available (llama3.1:8b, qwen2.5-coder:7b, mistral:7b)
- ❌ Model is timing out (too slow)
- ✅ Groq API key is configured and ready to use

## My Recommendation

**Use Groq for now** - it's much faster and will give you a better development experience. You can always switch back to Ollama later if needed.

To switch to Groq:
1. Update `.env`: `DEFAULT_LLM_PROVIDER=groq`
2. Restart backend server
3. Try your agent again

The workspace files issue is now fixed, so once you get the LLM working (either Ollama or Groq), you should see files appearing in the workspace!
