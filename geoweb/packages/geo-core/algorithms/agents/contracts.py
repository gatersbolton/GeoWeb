from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AgentRecommendRequest(BaseModel):
    user_prompt: str = ""
    artifact_tags: list[str] = Field(default_factory=list)
    noise_level: float = Field(default=0.0, ge=0.0, le=1.0)
    has_depth_meta: bool = True
    include_enhancement: bool = True
    prefer_speed: bool = False
    prefer_quality: bool = True
    prefer_decentralization_method: Literal["harmonic", "azimuth_equalization", "agc"] | None = None
    max_pipeline_steps: int = Field(default=3, ge=1, le=8)
    domain_context: dict[str, Any] = Field(default_factory=dict)


class CandidateScore(BaseModel):
    algo_id: str
    score: float
    reason: str


class AgentRecommendResponse(BaseModel):
    recommended_pipeline: list[str]
    recommended_configs: dict[str, dict[str, Any]]
    decision_log: dict[str, Any]
    candidates: list[CandidateScore]
    policy_used: str = "rules"
    follow_up_question: str | None = None


class AgentChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"] = "user"
    content: str


class AgentChatRequest(BaseModel):
    message: str
    history: list[AgentChatMessage] = Field(default_factory=list)
    recommend: AgentRecommendRequest | None = None
    stream: bool = False


class AgentChatResponse(BaseModel):
    answer: str
    recommendation: AgentRecommendResponse | None = None
    used_tools: list[str] = Field(default_factory=list)
    decision_log: dict[str, Any] = Field(default_factory=dict)


class AgentToolSpec(BaseModel):
    tool_id: str
    display_name: str
    category: str
    description: str
    status: Literal["active", "planned"] = "active"
    algo_id: str | None = None
    handles: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
