from __future__ import annotations

from typing import Any

from algorithms.agents.contracts import (
    AgentChatRequest,
    AgentChatResponse,
    AgentRecommendRequest,
    AgentRecommendResponse,
    AgentToolSpec,
)
from algorithms.agents.llm import (
    DashScopeCompatibleClient,
    LLMError,
    build_chat_system_prompt,
    build_recommendation_messages,
    extract_json_object,
)
from algorithms.agents.llm.prompts import build_llm_chat_messages
from algorithms.agents.policy.selector_rules import recommend as recommend_by_rules
from algorithms.agents.tools.registry import AgentToolRegistry, build_default_tool_registry
from algorithms.core.registry import AlgorithmRegistry

_ALLOWED_METHODS = {"harmonic", "azimuth_equalization", "agc"}
_ALLOWED_TAGS = {"stick_pull", "decentralization"}


class ATVExpertAgentService:
    def __init__(
        self,
        registry: AlgorithmRegistry,
        *,
        tool_registry: AgentToolRegistry | None = None,
        llm_client: DashScopeCompatibleClient | None = None,
    ) -> None:
        self._registry = registry
        self._tool_registry = tool_registry or build_default_tool_registry(registry)
        self._llm = llm_client or DashScopeCompatibleClient()

    def list_tools(self) -> list[AgentToolSpec]:
        return self._tool_registry.list_tools()

    def runtime_status(self) -> dict[str, Any]:
        status = self._llm.runtime_status()
        if status["llm_enabled"]:
            status["mode"] = "online"
            status["reason"] = "api_key_present"
        else:
            status["mode"] = "offline"
            status["reason"] = "missing_or_placeholder_api_key"
        return status

    def recommend(self, request: AgentRecommendRequest) -> AgentRecommendResponse:
        base_response = recommend_by_rules(request, self._registry)
        has_explicit_constraints = bool(request.artifact_tags or request.prefer_decentralization_method)
        if not request.user_prompt.strip() or not self._llm.is_enabled:
            base_response.decision_log["llm_used"] = False
            if request.user_prompt.strip() and not self._llm.is_enabled:
                base_response.decision_log["llm_reason"] = "missing_api_key_or_disabled"
            base_response.policy_used = "rules"
            return base_response
        if has_explicit_constraints:
            base_response.decision_log["llm_used"] = False
            base_response.decision_log["llm_reason"] = "explicit_constraints_already_provided"
            base_response.policy_used = "rules"
            return base_response

        try:
            llm_hints = self._infer_hints_from_llm(request)
        except LLMError as exc:
            base_response.decision_log["llm_used"] = False
            base_response.decision_log["llm_error"] = str(exc)
            base_response.policy_used = "rules"
            return base_response

        merged_request = _merge_request_with_hints(request, llm_hints)
        merged_response = recommend_by_rules(merged_request, self._registry)
        merged_response.policy_used = "llm+rules"
        merged_response.decision_log["llm_used"] = True
        merged_response.decision_log["llm_model"] = self._llm.config.model
        merged_response.decision_log["llm_hints"] = llm_hints
        return merged_response

    def chat(self, request: AgentChatRequest) -> AgentChatResponse:
        used_tools: list[str] = []
        recommendation = None
        if _looks_like_recommendation_request(request.message) or request.recommend is not None:
            recommend_request = request.recommend or AgentRecommendRequest(user_prompt=request.message)
            if request.recommend is not None and not recommend_request.user_prompt.strip():
                recommend_request.user_prompt = request.message
            recommendation = self.recommend(recommend_request)
            used_tools.append("tool:recommend_pipeline")

        if not self._llm.is_enabled:
            answer = _fallback_answer(request.message, recommendation)
            return AgentChatResponse(
                answer=answer,
                recommendation=recommendation,
                used_tools=used_tools,
                decision_log={"llm_used": False, "reason": "missing_api_key_or_disabled"},
            )

        try:
            system_prompt = build_chat_system_prompt(self._tool_registry.list_tools())
            history = [{"role": item.role, "content": item.content} for item in request.history]
            recommendation_summary = None
            if recommendation is not None:
                recommendation_summary = {
                    "pipeline": recommendation.recommended_pipeline,
                    "reason": recommendation.decision_log.get("final_choice_reason"),
                }
            messages = build_llm_chat_messages(
                system_prompt=system_prompt,
                history=history,
                user_message=request.message,
                recommendation_summary=recommendation_summary,
            )
            answer = self._llm.chat(messages, purpose="chat_reply")
            return AgentChatResponse(
                answer=answer.strip(),
                recommendation=recommendation,
                used_tools=used_tools,
                decision_log={"llm_used": True, "model": self._llm.config.model},
            )
        except LLMError as exc:
            answer = _fallback_answer(request.message, recommendation, llm_error=str(exc))
            return AgentChatResponse(
                answer=answer,
                recommendation=recommendation,
                used_tools=used_tools,
                decision_log={"llm_used": False, "llm_error": str(exc)},
            )

    def _infer_hints_from_llm(self, request: AgentRecommendRequest) -> dict[str, Any]:
        tools = self._tool_registry.list_active_tools()
        messages = build_recommendation_messages(request, tools)
        raw_content = self._llm.chat(
            messages,
            temperature=0.0,
            max_tokens=300,
            purpose="recommendation_hint",
        )
        payload = extract_json_object(raw_content)
        if not payload:
            raise LLMError("LLM recommendation response is not a JSON object.")
        return _normalize_llm_hints(payload)


def _normalize_llm_hints(payload: dict[str, Any]) -> dict[str, Any]:
    tags = payload.get("artifact_tags", [])
    if isinstance(tags, str):
        tags = [tags]
    if not isinstance(tags, list):
        tags = []
    normalized_tags = sorted({str(tag).strip().lower() for tag in tags if str(tag).strip().lower() in _ALLOWED_TAGS})

    method = payload.get("prefer_decentralization_method")
    if isinstance(method, str):
        method = method.strip().lower()
    else:
        method = None
    if method not in _ALLOWED_METHODS:
        method = None

    include = payload.get("include_enhancement")
    include_enhancement = include if isinstance(include, bool) else None

    confidence_raw = payload.get("confidence")
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        confidence = 0.5
    confidence = max(0.0, min(1.0, confidence))

    reason = str(payload.get("reason", "")).strip()
    return {
        "artifact_tags": normalized_tags,
        "include_enhancement": include_enhancement,
        "prefer_decentralization_method": method,
        "confidence": confidence,
        "reason": reason,
    }


def _merge_request_with_hints(
    request: AgentRecommendRequest,
    llm_hints: dict[str, Any],
) -> AgentRecommendRequest:
    data = _model_dump(request)
    existing_tags = data.get("artifact_tags", [])
    merged_tags = sorted(set(existing_tags) | set(llm_hints.get("artifact_tags", [])))
    data["artifact_tags"] = merged_tags

    if data.get("prefer_decentralization_method") is None:
        hinted_method = llm_hints.get("prefer_decentralization_method")
        if hinted_method in _ALLOWED_METHODS:
            data["prefer_decentralization_method"] = hinted_method

    hinted_include = llm_hints.get("include_enhancement")
    if isinstance(hinted_include, bool) and data.get("include_enhancement", True):
        data["include_enhancement"] = hinted_include

    return AgentRecommendRequest(**data)


def _looks_like_recommendation_request(message: str) -> bool:
    text = (message or "").lower()
    if not text:
        return False
    indicators = [
        "推荐",
        "recommend",
        "去伪影",
        "stick_pull",
        "decentralization",
        "算法",
        "pipeline",
        "增强",
        "超分",
        "super resolution",
        "enhance",
        "裂隙",
        "崩落",
    ]
    return any(token in text for token in indicators)


def _fallback_answer(
    message: str,
    recommendation: AgentRecommendResponse | None,
    *,
    llm_error: str | None = None,
) -> str:
    text = (message or "").strip()
    lower = text.lower()
    error_tip = ""
    if llm_error:
        error_tip = f"（在线调用失败：{llm_error}）"

    if recommendation is not None:
        pipeline = " -> ".join(recommendation.recommended_pipeline)
        return (
            f"建议先按 pipeline 执行：{pipeline}。{error_tip}"
            "如需进一步细化参数，请补充样本分辨率、噪声等级和目标解释任务。"
        )

    if not text:
        return f"你可以直接描述问题，或上传 ATV 图像让我分析。{error_tip}"

    if any(token in lower for token in ("hello", "hi", "hey")) or any(
        token in text for token in ("你好", "您好", "哈喽")
    ):
        return f"你好，我是 ATV 专家 Agent。你可以直接问我去伪影、参数选择或解释分析流程。{error_tip}"

    if "who are you" in lower or any(token in text for token in ("你是谁", "你是做什么的")):
        return (
            "我是 ATV 专家 Agent，负责去伪影算法选择、参数建议与图像处理流程分析。"
            f"上传图像后我也可以直接执行算法并返回结果。{error_tip}"
        )

    if any(token in lower for token in ("help", "what can you do", "capability")) or any(
        token in text for token in ("能做什么", "可以做什么", "怎么用", "帮助")
    ):
        return (
            "我目前支持：1) 去伪影算法推荐；2) 图像增强/超分；3) 图像上传后自动执行 pipeline；"
            f"4) 返回结果预览与下载。你可以先发一条目标描述，例如“去除去中心化伪影”或“做 4 倍超分增强”。{error_tip}"
        )

    if any(token in lower for token in ("thanks", "thank you")) or any(
        token in text for token in ("谢谢", "感谢")
    ):
        return f"不客气。你可以继续发图或描述目标，我会给出下一步处理建议。{error_tip}"

    brief = text if len(text) <= 24 else text[:24] + "..."
    return (
        f"我理解你在问“{brief}”。我当前处于离线规则对话模式。"
        f"如果你希望我给出算法方案，请描述伪影类型（如 stick_pull、去中心化）或直接上传图像。{error_tip}"
    )


def _model_dump(model: Any) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()
