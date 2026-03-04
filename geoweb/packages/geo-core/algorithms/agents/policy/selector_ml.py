from __future__ import annotations

from algorithms.agents.contracts import AgentRecommendRequest, AgentRecommendResponse
from algorithms.agents.policy.selector_rules import recommend as recommend_by_rules
from algorithms.core.registry import AlgorithmRegistry


def recommend(request: AgentRecommendRequest, registry: AlgorithmRegistry) -> AgentRecommendResponse:
    response = recommend_by_rules(request, registry)
    response.decision_log["policy"] = "ml_placeholder"
    response.decision_log["model"] = "not_implemented_yet"
    response.policy_used = "ml_placeholder"
    return response
