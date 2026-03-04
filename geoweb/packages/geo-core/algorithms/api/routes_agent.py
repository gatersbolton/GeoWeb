from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from algorithms.api.runtime import AGENT_SERVICE
from algorithms.api.schemas import (
    AgentChatRequestSchema,
    AgentChatResponseSchema,
    AgentRecommendRequestSchema,
    AgentRecommendResponseSchema,
    AgentToolSchema,
)

router = APIRouter()


def _model_dump(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


@router.post("/agent/recommend", response_model=AgentRecommendResponseSchema)
def agent_recommend(request: AgentRecommendRequestSchema) -> AgentRecommendResponseSchema:
    response = AGENT_SERVICE.recommend(request)
    return AgentRecommendResponseSchema(**_model_dump(response))


@router.post("/agent/chat", response_model=AgentChatResponseSchema)
def agent_chat(request: AgentChatRequestSchema) -> AgentChatResponseSchema:
    response = AGENT_SERVICE.chat(request)
    return AgentChatResponseSchema(**_model_dump(response))


@router.get("/agent/tools", response_model=list[AgentToolSchema])
def list_agent_tools() -> list[AgentToolSchema]:
    tools = AGENT_SERVICE.list_tools()
    return [AgentToolSchema(**_model_dump(tool)) for tool in tools]
