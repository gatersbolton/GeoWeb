from __future__ import annotations

from typing import Any

from algorithms.agents.contracts import AgentRecommendRequest, AgentRecommendResponse, CandidateScore
from algorithms.core.registry import AlgorithmRegistry

KNOWN_ARTIFACT_TAGS = ("stick_pull", "decentralization")
DEFAULT_ARTIFACT_PIPELINE = ("artifact.stick_pull.v1", "artifact.decentralization.v1")
DEFAULT_ENHANCEMENT_ALGO = "enhancement.super_resolution.v1"

_STICK_PULL_HINTS = (
    "stick_pull",
    "stick pull",
    "stick-and-pull",
    "拉伸",
    "拖拽",
    "纵向畸变",
    "速度不稳",
    "拉压伪影",
)
_DECENTRALIZATION_HINTS = (
    "decentralization",
    "decentralized",
    "去中心",
    "偏心",
    "环向偏置",
    "方位偏置",
    "azimuth bias",
    "column bias",
)
_ENHANCEMENT_HINTS = (
    "enhance",
    "enhancement",
    "super resolution",
    "super-resolution",
    "清晰",
    "锐化",
    "增强",
)
_DISABLE_ENHANCEMENT_HINTS = ("不要增强", "不做增强", "no enhancement", "without enhancement")
_METHOD_HINTS = {
    "harmonic": ("harmonic", "谐波"),
    "azimuth_equalization": ("azimuth_equalization", "equalization", "均衡", "均衡化"),
    "agc": ("agc", "自动增益", "增益控制"),
}


def _model_dump(model: CandidateScore) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def infer_prompt_hints(prompt: str) -> dict[str, Any]:
    text = (prompt or "").strip().lower()
    if not text:
        return {
            "artifact_tags": [],
            "include_enhancement": None,
            "prefer_decentralization_method": None,
            "matched_tokens": {},
        }

    matched_tokens: dict[str, list[str]] = {}
    artifact_tags: set[str] = set()

    stick_hits = [token for token in _STICK_PULL_HINTS if token in text]
    if stick_hits:
        artifact_tags.add("stick_pull")
        matched_tokens["stick_pull"] = stick_hits

    decentralization_hits = [token for token in _DECENTRALIZATION_HINTS if token in text]
    if decentralization_hits:
        artifact_tags.add("decentralization")
        matched_tokens["decentralization"] = decentralization_hits

    include_enhancement: bool | None = None
    enhancement_hits = [token for token in _ENHANCEMENT_HINTS if token in text]
    if enhancement_hits:
        include_enhancement = True
        matched_tokens["enhancement"] = enhancement_hits
    disable_enhancement_hits = [token for token in _DISABLE_ENHANCEMENT_HINTS if token in text]
    if disable_enhancement_hits:
        include_enhancement = False
        matched_tokens["enhancement_disabled"] = disable_enhancement_hits

    prefer_decentralization_method = None
    for method, tokens in _METHOD_HINTS.items():
        hits = [token for token in tokens if token in text]
        if hits:
            prefer_decentralization_method = method
            matched_tokens["decentralization_method"] = hits
            break

    return {
        "artifact_tags": sorted(artifact_tags),
        "include_enhancement": include_enhancement,
        "prefer_decentralization_method": prefer_decentralization_method,
        "matched_tokens": matched_tokens,
    }


def _merge_tags(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    for group in groups:
        for tag in group:
            if tag in KNOWN_ARTIFACT_TAGS and tag not in merged:
                merged.append(tag)
    return merged


def _resolve_include_enhancement(
    request: AgentRecommendRequest,
    prompt_hints: dict[str, Any],
) -> bool:
    hinted = prompt_hints["include_enhancement"]
    if hinted is None:
        return request.include_enhancement
    # Explicit API request takes precedence over prompt hints when disabled.
    if request.include_enhancement is False:
        return False
    return bool(hinted)


def _resolve_decentralization_method(
    request: AgentRecommendRequest,
    prompt_hints: dict[str, Any],
) -> str | None:
    return request.prefer_decentralization_method or prompt_hints["prefer_decentralization_method"]


def _candidate_score(
    *,
    algo_id: str,
    capability: dict[str, Any],
    tags: list[str],
    include_enhancement: bool,
    request: AgentRecommendRequest,
) -> CandidateScore:
    handles = set(capability.get("handles_artifact_types", []))
    matched = handles.intersection(tags)
    reason_parts: list[str] = []
    score = 0.25

    if matched:
        score += 0.5
        reason_parts.append(f"artifact tag match: {', '.join(sorted(matched))}")
    elif algo_id.startswith("artifact.") and not tags:
        score += 0.2
        reason_parts.append("default artifact candidate")

    if algo_id.startswith("enhancement."):
        if include_enhancement:
            score += 0.2
            reason_parts.append("enhancement requested")
        else:
            score -= 0.2
            reason_parts.append("enhancement disabled")

    cost_profile = capability.get("cost_profile", {})
    runtime = str(cost_profile.get("runtime", "medium")).lower()
    if request.prefer_speed and runtime == "low":
        score += 0.08
        reason_parts.append("prefer_speed=on and low runtime")
    if request.prefer_quality and capability.get("output_characteristics", {}).get("edge_preservation") in {
        "high",
        "method-dependent",
    }:
        score += 0.06
        reason_parts.append("prefer_quality=on and edge-preserving")

    score = max(0.0, min(1.0, score))
    if not reason_parts:
        reason_parts = ["general candidate"]
    return CandidateScore(algo_id=algo_id, score=score, reason="; ".join(reason_parts))


def _build_pipeline(
    *,
    tags: list[str],
    include_enhancement: bool,
    max_pipeline_steps: int,
    registry: AlgorithmRegistry,
) -> list[str]:
    available = set(registry.list_algo_ids())
    pipeline: list[str] = []

    if tags:
        for tag in KNOWN_ARTIFACT_TAGS:
            if tag not in tags:
                continue
            expected = f"artifact.{tag}.v1"
            if expected in available and expected not in pipeline:
                pipeline.append(expected)
    else:
        for algo_id in DEFAULT_ARTIFACT_PIPELINE:
            if algo_id in available and algo_id not in pipeline:
                pipeline.append(algo_id)

    if include_enhancement and DEFAULT_ENHANCEMENT_ALGO in available:
        pipeline.append(DEFAULT_ENHANCEMENT_ALGO)

    if not pipeline:
        for algo_id in registry.list_algo_ids():
            pipeline.append(algo_id)
            if len(pipeline) >= max_pipeline_steps:
                break

    return pipeline[:max_pipeline_steps]


def _build_recommended_configs(
    *,
    pipeline: list[str],
    registry: AlgorithmRegistry,
    prefer_decentralization_method: str | None,
) -> dict[str, dict[str, Any]]:
    recommended_configs: dict[str, dict[str, Any]] = {}
    for algo_id in pipeline:
        config = registry.get(algo_id).get_default_config()
        if algo_id == "artifact.decentralization.v1" and prefer_decentralization_method:
            safe_cfg = dict(config.get("safe", {}))
            safe_cfg["method"] = prefer_decentralization_method
            config = dict(config)
            config["safe"] = safe_cfg
        recommended_configs[algo_id] = config
    return recommended_configs


def recommend(request: AgentRecommendRequest, registry: AlgorithmRegistry) -> AgentRecommendResponse:
    prompt_hints = infer_prompt_hints(request.user_prompt)
    tags = _merge_tags(request.artifact_tags, prompt_hints["artifact_tags"])
    include_enhancement = _resolve_include_enhancement(request, prompt_hints)
    method = _resolve_decentralization_method(request, prompt_hints)

    candidates = [
        _candidate_score(
            algo_id=descriptor.algorithm.algo_id,
            capability=descriptor.capability,
            tags=tags,
            include_enhancement=include_enhancement,
            request=request,
        )
        for descriptor in registry.list_descriptors()
    ]
    candidates.sort(key=lambda item: item.score, reverse=True)

    pipeline = _build_pipeline(
        tags=tags,
        include_enhancement=include_enhancement,
        max_pipeline_steps=request.max_pipeline_steps,
        registry=registry,
    )
    recommended_configs = _build_recommended_configs(
        pipeline=pipeline,
        registry=registry,
        prefer_decentralization_method=method,
    )

    decision_log = {
        "policy": "rules",
        "input_quality_eval": {
            "artifact_tags": request.artifact_tags,
            "noise_level": request.noise_level,
            "has_depth_meta": request.has_depth_meta,
            "user_prompt": request.user_prompt,
            "domain_context": request.domain_context,
        },
        "prompt_hints": prompt_hints,
        "effective_tags": tags,
        "include_enhancement": include_enhancement,
        "candidate_scores": [_model_dump(candidate) for candidate in candidates],
        "final_choice_reason": "rule-based routing with prompt keyword parsing",
        "parameter_basis": "algorithm default configs + prompt hints",
    }

    follow_up_question = None
    if not tags and request.user_prompt.strip():
        follow_up_question = "可补充伪影类型（stick_pull/decentralization）或样本特征，以提高推荐准确度。"

    return AgentRecommendResponse(
        recommended_pipeline=pipeline,
        recommended_configs=recommended_configs,
        decision_log=decision_log,
        candidates=candidates,
        policy_used="rules",
        follow_up_question=follow_up_question,
    )
