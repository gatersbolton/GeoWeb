from algorithms.agents.contracts import AgentChatRequest, AgentRecommendRequest
from algorithms.agents.service import ATVExpertAgentService
from algorithms.agents.tools.registry import build_default_tool_registry
from algorithms.bootstrap import build_default_registry


class _FakeLLMClient:
    def __init__(self, payload: str, *, enabled: bool = True) -> None:
        self._payload = payload
        self._enabled = enabled
        self.config = type("Cfg", (), {"model": "fake-model"})()

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def chat(self, messages, **kwargs):  # noqa: ANN001
        return self._payload


def test_service_merges_llm_hints_into_recommendation() -> None:
    registry = build_default_registry()
    tools = build_default_tool_registry(registry)
    llm = _FakeLLMClient(
        '{"artifact_tags":["decentralization"],"prefer_decentralization_method":"azimuth_equalization","include_enhancement":false,"confidence":0.9,"reason":"match"}'
    )
    service = ATVExpertAgentService(registry, tool_registry=tools, llm_client=llm)
    response = service.recommend(AgentRecommendRequest(user_prompt="有偏心伪影，走均衡法"))
    assert response.policy_used == "llm+rules"
    assert response.recommended_pipeline[0] == "artifact.decentralization.v1"
    assert "enhancement.super_resolution.v1" not in response.recommended_pipeline
    assert (
        response.recommended_configs["artifact.decentralization.v1"]["safe"]["method"]
        == "azimuth_equalization"
    )


def test_service_chat_fallback_without_llm() -> None:
    registry = build_default_registry()
    tools = build_default_tool_registry(registry)
    llm = _FakeLLMClient("", enabled=False)
    service = ATVExpertAgentService(registry, tool_registry=tools, llm_client=llm)
    response = service.chat(AgentChatRequest(message="推荐一个去伪影方案"))
    assert response.recommendation is not None
    assert response.decision_log["llm_used"] is False
    assert len(response.answer) > 0


def test_service_chat_smalltalk_without_llm_does_not_force_recommendation() -> None:
    registry = build_default_registry()
    tools = build_default_tool_registry(registry)
    llm = _FakeLLMClient("", enabled=False)
    service = ATVExpertAgentService(registry, tool_registry=tools, llm_client=llm)
    response = service.chat(AgentChatRequest(message="你是谁"))
    assert response.recommendation is None
    assert response.decision_log["llm_used"] is False
    assert "ATV" in response.answer


def test_service_chat_groove_prompt_without_llm_routes_to_groovemask() -> None:
    registry = build_default_registry()
    tools = build_default_tool_registry(registry)
    llm = _FakeLLMClient("", enabled=False)
    service = ATVExpertAgentService(registry, tool_registry=tools, llm_client=llm)
    response = service.chat(AgentChatRequest(message="帮我去掉这张图里的槽沟伪影"))
    assert response.recommendation is not None
    assert response.recommendation.recommended_pipeline == ["artifact.groovemask.v1"]


def test_service_chat_enhancement_prompt_without_llm_returns_enhancement_pipeline() -> None:
    registry = build_default_registry()
    tools = build_default_tool_registry(registry)
    llm = _FakeLLMClient("", enabled=False)
    service = ATVExpertAgentService(registry, tool_registry=tools, llm_client=llm)
    response = service.chat(AgentChatRequest(message="请直接做 4 倍超分增强"))
    assert response.recommendation is not None
    assert response.recommendation.recommended_pipeline == ["enhancement.super_resolution.v1"]
    config = response.recommendation.recommended_configs["enhancement.super_resolution.v1"]
    assert config["advanced"]["outscale"] == 4.0
    assert config["advanced"]["detail_strength"] == 0.72


def test_service_chat_artifact_only_prompt_without_llm_does_not_append_enhancement() -> None:
    registry = build_default_registry()
    tools = build_default_tool_registry(registry)
    llm = _FakeLLMClient("", enabled=False)
    service = ATVExpertAgentService(registry, tool_registry=tools, llm_client=llm)
    response = service.chat(AgentChatRequest(message="帮我给它去除去中心化的伪影"))
    assert response.recommendation is not None
    assert response.recommendation.recommended_pipeline == ["artifact.decentralization.v1"]


def test_service_tool_registry_includes_dlis_visualization() -> None:
    registry = build_default_registry()
    tools = build_default_tool_registry(registry)
    tool_ids = {item.tool_id for item in tools.list_tools()}
    assert "dlis.visualize.v1" in tool_ids
