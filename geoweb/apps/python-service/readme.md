# apps/python-service

Purpose
- FastAPI service for compute and visualization.

Contents
- python_service/: application package.
- requirements.txt: runtime dependencies.
- Dockerfile: container build.

Notes
- Uvicorn entry is python_service.app:app.
- Depends on packages/compute algorithms and packages/geo-core artifacts.
- Default port is 8000.
- Augmentation API: POST `/api/augmentation/run` for stick-and-pull artifact removal.
