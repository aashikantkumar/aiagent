# Architecture

MyAIAgent follows a modular, monolithic architecture split into a backend and a frontend, leveraging OpenHands patterns for sandbox execution.

## Components

1. **Frontend (React + Vite + Tailwind + TanStack Query)**
   - Communicates with the backend via REST API and WebSockets.
   - Manages state using Zustand for client-side state and TanStack Query for server state.

2. **Backend (FastAPI + Python)**
   - Exposes a REST API for session management, secrets, and configuration.
   - Uses WebSockets to stream the reasoning and execution logs of the agent in real-time.
   - Implements a service layer (`ConversationService`, `SandboxService`, `SecretsService`) to separate business logic from routing.

3. **Agent Engine (LangGraph + LiteLLM)**
   - State-machine based reasoning engine powered by LangGraph.
   - Utilizes `LLMFactory` to instantiate LLMs dynamically (Groq, Ollama, Anthropic, OpenAI).

4. **Sandbox Execution (Docker Runtime)**
   - Isolates code execution in a Docker container (OpenHands pattern).
   - Manages container lifecycle, pauses/resumes, and cleans up resources.
