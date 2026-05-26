# MyAIAgent

An autonomous AI coding agent with a FastAPI backend and a React/Vite frontend. It uses a LangGraph-based engine with Groq integration and Docker container sandboxing for safe code execution (OpenHands-like patterns).

## Configuration

To set up your project, create a `.env` file in the `backend/` directory (you can copy `backend/config.template.toml` to `.env` or just create `.env`).

Required environment variables:
```
GROQ_API_KEY=your_groq_api_key
OLLAMA_BASE_URL=http://localhost:11434  # If using Ollama
```

## Quick Start

We provide Makefiles to simplify the development process.

### 1. Setup

Run the following command in the root directory to install both frontend and backend dependencies:
```bash
make install
```

### 2. Development Servers

Start both backend and frontend development servers concurrently:
```bash
make dev
```

Alternatively, you can run them individually:
```bash
make dev-backend
make dev-frontend
```

### 3. Testing and Linting

Run all tests:
```bash
make test
```

Run linters (Ruff for backend, ESLint for frontend):
```bash
make lint
```

Run formatters (Ruff for backend, Prettier for frontend):
```bash
make format
```

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design and architecture overview.
- [DEVELOPMENT.md](DEVELOPMENT.md) - Detailed guide on local development, testing, and contribution.
# aiagent
