# api

FastAPI routes for algorithm execution and agent interaction.

- `routes_algorithms.py`: list algorithms and capability metadata.
- `routes_jobs.py`: submit/query pipeline jobs.
- `routes_agent.py`: ATV expert agent endpoints.
- `schemas.py`: request/response contracts.
- `runtime.py`: shared registry, job store, and agent service singletons.

## Agent Endpoints

- `POST /agent/recommend`
- `POST /agent/chat`
- `GET /agent/tools`
