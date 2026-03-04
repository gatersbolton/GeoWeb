# apps/python-service

Purpose
- FastAPI service for compute and visualization.

Contents
- python_service/: application package.
- requirements.txt: runtime dependencies.
- Dockerfile: container build.

Notes
- Uvicorn entry is python_service.app:app.
- Depends on packages/compute algorithms and packages/geo-core algorithms/agent modules.
- Default port is 8000.
- Augmentation API: POST `/api/augmentation/run` for stick-and-pull artifact removal.
- Agent APIs:
  - POST `/api/agent/chat` (chat + optional image upload + auto algorithm execution)
  - POST `/api/agent/recommend`
  - GET `/api/agent/tools`
  - GET `/api/agent/runtime` (online/offline + model/log path)
- Optional LLM env file:
  - Copy `.env.agent.example` to `.env.agent.local`.
  - Service auto-loads `.env.agent.local` on startup, so `start.bat` keeps one-click flow.
- LLM call logs:
  - default file: `apps/python-service/logs/agent_llm_calls.jsonl`
  - configurable via `GEO_AGENT_LLM_LOG_PATH`
