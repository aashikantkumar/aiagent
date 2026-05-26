# Development Guide

Welcome to the development guide for MyAIAgent. 

## Prerequisites
- Node.js (v20+)
- Python (3.11+)
- Docker (for sandbox execution)

## Make Targets
We use `make` for consistent tooling across the project:
- `make install` - Installs virtual environments, `pip` packages, and `npm` modules.
- `make dev` - Runs both backend and frontend servers in parallel.
- `make test` - Runs pytest in the backend and vitest in the frontend.
- `make lint` - Runs Ruff and ESLint.
- `make format` - Formats code using Ruff and Prettier.
- `make clean` - Cleans cache files, `node_modules`, and `venv`.

## Backend Guidelines
- Add new endpoints in `backend/routes/`.
- Keep business logic in `backend/services/`.
- Add tests to `backend/tests/`. We use `pytest`.
- Linting uses `ruff`. Check your code with `make lint` before committing.

## Frontend Guidelines
- React components belong in `frontend/src/components/`.
- API calls and queries belong in `frontend/src/api/` (using TanStack Query).
- Zustand is used for client-side state.
- Add unit tests for hooks and complex logic using Vitest in `frontend/src/**/__tests__/`.
