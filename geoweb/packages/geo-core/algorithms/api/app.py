from __future__ import annotations

from fastapi import FastAPI

from algorithms.api.routes_agent import router as agent_router
from algorithms.api.routes_algorithms import router as algorithms_router
from algorithms.api.routes_jobs import router as jobs_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="GeoWeb Artifact Removal Framework",
        version="0.2.0",
        description="ATV artifact-removal framework with expert agent recommendation/chat.",
    )
    app.include_router(algorithms_router)
    app.include_router(jobs_router)
    app.include_router(agent_router)
    return app


app = create_app()
