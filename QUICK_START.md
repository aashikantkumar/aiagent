# ⚡ Quick Start Guide - AI Agent Application

## 🎯 What You Need

**1. Get a FREE Groq API Key (Recommended)**
- Visit: https://console.groq.com/
- Sign up (free)
- Create API Key
- Copy the key (starts with `gsk_`)

**Alternative Options:**
- OpenAI: https://platform.openai.com/ (paid)
- Anthropic: https://console.anthropic.com/ (paid)
- Ollama: https://ollama.com/ (free, local)

---

## 🚀 5-Minute Setup

### 1. Start Infrastructure
```bash
cd "/media/aashikant/GAME Volume/aicode/myaiagent"
docker compose up -d
```

### 2. Configure API Key
```bash
cd backend
nano .env  # or use any text editor
```

Add this line (replace with your actual key):
```env
GROQ_API_KEY=gsk_your_actual_key_here
DEFAULT_LLM_PROVIDER=groq
```

### 3. Setup Backend
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python migrations/run_migrations.py
```

### 4. Start Backend
```bash
PORT=8001 python main.py
```

### 5. Setup & Start Frontend
```bash
# In a new terminal
cd frontend
npm install
npm run dev
```

### 6. Open Browser
```
http://localhost:5173
```

---

## 💡 First Use

1. **Open the app** in your browser
2. **Type a request** like: "Create a simple calculator app"
3. **Watch the magic** happen:
   - Agent plans the implementation
   - Writes the code
   - Executes it in a sandbox
   - Shows you the results

---

## 🔑 API Key Options

### Option 1: Groq (FREE & FAST) ⭐ Recommended
```env
DEFAULT_LLM_PROVIDER=groq
DEFAULT_LLM_MODEL=groq/llama-3.3-70b-versatile
GROQ_API_KEY=gsk_your_key_here
```
- ✅ Free tier with generous limits
- ✅ Fastest inference (10x faster)
- ✅ Great for coding tasks

### Option 2: OpenAI (GPT-4)
```env
DEFAULT_LLM_PROVIDER=openai
DEFAULT_LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-your_key_here
```
- 💰 Pay-as-you-go (~$0.03/1K tokens)
- ✅ Most capable model

### Option 3: Anthropic (Claude)
```env
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-your_key_here
```
- 💰 Pay-as-you-go (~$0.015/1K tokens)
- ✅ Great reasoning abilities

### Option 4: Ollama (Local, FREE)
```bash
# Install Ollama first
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama
ollama serve

# Pull a model
ollama pull qwen2.5-coder:7b
```

Then in `.env`:
```env
DEFAULT_LLM_PROVIDER=ollama
DEFAULT_LLM_MODEL=ollama/qwen2.5-coder:7b
OLLAMA_BASE_URL=http://localhost:11434
# No API key needed!
```

---

## 📝 Complete .env File Example

```env
# LLM Configuration (choose one provider)
DEFAULT_LLM_PROVIDER=groq
DEFAULT_LLM_MODEL=groq/llama-3.3-70b-versatile
GROQ_API_KEY=gsk_your_actual_key_here

# Database (default values - don't change unless needed)
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5433
POSTGRES_USER=langgraph
POSTGRES_PASSWORD=langgraph_password
POSTGRES_DB=agent_state

# Redis (default values)
REDIS_HOST=localhost
REDIS_PORT=6379

# Server
DEBUG=false
HOST=0.0.0.0
PORT=8001

# Secrets Encryption (generate with command below)
SECRETS_FERNET_KEY=your_generated_key_here

# Sandbox
SANDBOX_CLEANUP_INTERVAL=3600
```

**Generate Secrets Key:**
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 🔧 Common Commands

### Check if services are running
```bash
docker compose ps
```

### View backend logs
```bash
cd backend
tail -f logs/app.log  # if logging to file
```

### Restart everything
```bash
# Stop all
docker compose down
pkill -f "python main.py"
pkill -f "npm run dev"

# Start again
docker compose up -d
cd backend && PORT=8001 python main.py &
cd frontend && npm run dev &
```

### Test API
```bash
# Health check
curl http://localhost:8001/

# Create session
curl -X POST http://localhost:8001/api/agent/sessions

# List profiles
curl http://localhost:8001/api/settings/llm-profiles
```

---

## ❌ Troubleshooting

### "GROQ_API_KEY not found"
- Check `.env` file exists in `backend/` directory
- Verify key starts with `gsk_`
- Restart backend

### "Connection refused" to database
```bash
docker compose up -d
docker compose ps  # Check if postgres is running
```

### "Port already in use"
```bash
# Use different port
PORT=8002 python main.py
```

### Frontend can't connect
- Check backend is running: `curl http://localhost:8001/`
- Check port is 8001 (not 8000)

---

## 📚 More Help

- **Full Guide:** See `USER_GUIDE.md`
- **Architecture:** See `ARCHITECTURE.md`
- **Development:** See `DEVELOPMENT.md`
- **API Docs:** http://localhost:8001/docs (when running)

---

## ✅ Checklist

- [ ] Got Groq API key from https://console.groq.com/
- [ ] Created `backend/.env` with API key
- [ ] Started Docker: `docker compose up -d`
- [ ] Ran migrations: `python migrations/run_migrations.py`
- [ ] Started backend: `PORT=8001 python main.py`
- [ ] Started frontend: `npm run dev`
- [ ] Opened http://localhost:5173
- [ ] Tested with a simple request

---

## 🎉 You're Ready!

Your AI Agent is now ready to help you build software. Just type what you want to create and watch it happen!

**Example requests to try:**
- "Create a todo app with React"
- "Build a simple calculator"
- "Make a weather app that uses an API"
- "Create a markdown editor"

**Happy coding! 🚀**
