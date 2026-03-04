# apps/python-service/python_service

Purpose
- FastAPI app source code.

Contents
- app.py: FastAPI app setup and routers.
- api/: HTTP endpoints for borehole/stress inversion/augmentation/agent.
- services/: async runners and progress updates.
- thirdparty/: thin wrappers around research code.
- core/: path resolution and progress state.

Notes
- core/paths.py defines repo-relative locations.
- app.py auto-loads optional local env files for agent LLM:
  - `apps/python-service/.env.agent.local`
  - `packages/geo-core/configs/env/agent.env.local`
