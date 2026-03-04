from algorithms.agents.contracts import AgentRecommendRequest
from algorithms.agents.policy.selector_rules import infer_prompt_hints, recommend
from algorithms.bootstrap import build_default_registry


def test_infer_prompt_hints_detects_artifact_and_method() -> None:
    hints = infer_prompt_hints("请使用 agc 方法去除去中心伪影，并增强图像")
    assert "decentralization" in hints["artifact_tags"]
    assert hints["prefer_decentralization_method"] == "agc"
    assert hints["include_enhancement"] is True


def test_recommend_uses_prompt_when_tags_missing() -> None:
    registry = build_default_registry()
    response = recommend(
        AgentRecommendRequest(
            user_prompt="这个样本有明显 stick pull 拉伸伪影",
            artifact_tags=[],
        ),
        registry,
    )
    assert response.recommended_pipeline[0] == "artifact.stick_pull.v1"


def test_recommend_applies_decentralization_method_hint() -> None:
    registry = build_default_registry()
    response = recommend(
        AgentRecommendRequest(
            user_prompt="处理偏心，用 harmonic 方法，不做增强",
        ),
        registry,
    )
    assert "artifact.decentralization.v1" in response.recommended_pipeline
    config = response.recommended_configs["artifact.decentralization.v1"]
    assert config["safe"]["method"] == "harmonic"
    assert "enhancement.super_resolution.v1" not in response.recommended_pipeline
