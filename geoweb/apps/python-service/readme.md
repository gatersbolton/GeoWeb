# apps/python-service

Purpose
- FastAPI service for compute and visualization.

Contents
- python_service/: application package.
- requirements.txt: runtime dependencies.
- Dockerfile: container build.

Notes
- Uvicorn entry is python_service.app:app.
- Depends on packages/compute algorithms.
- Default port is 8000.
