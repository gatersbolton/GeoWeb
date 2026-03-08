from __future__ import annotations

import json
from typing import Any

from algorithms.agents.contracts import AgentRecommendRequest, AgentToolSpec


def build_chat_system_prompt(tools: list[AgentToolSpec]) -> str:
    tool_lines = []
    for tool in tools:
        status = "可用" if tool.status == "active" else "规划中"
        suffix = f" -> {tool.algo_id}" if tool.algo_id else ""
        tool_lines.append(f"- {tool.tool_id} ({status}){suffix}: {tool.description}")
    tool_text = "\n".join(tool_lines) if tool_lines else "- 暂无工具"
    return (
        "你是 ATV 成像解释与处理专家。请使用专业、可执行、可追溯的建议回答用户。\n"
        "当用户询问去伪影方案时，优先给出算法选择理由、参数建议、适用边界。\n"
        "当前可用/规划工具如下：\n"
        f"{tool_text}\n"
        "如果用户问题缺少关键信息，请指出最小补充信息。"
    )


def build_recommendation_messages(
    request: AgentRecommendRequest,
    tools: list[AgentToolSpec],
) -> list[dict[str, str]]:
    tool_payload = [
        {
            "tool_id": tool.tool_id,
            "status": tool.status,
            "algo_id": tool.algo_id,
            "handles": tool.handles,
            "description": tool.description,
            "metadata": tool.metadata,
        }
        for tool in tools
    ]
    system_prompt = (
        "你是 ATV 去伪影路由专家。"
        "请从用户提示中识别伪影类型和参数偏好，仅返回 JSON 对象，键必须包含：\n"
        "artifact_tags: string[] (候选值: stick_pull, decentralization)\n"
        "include_enhancement: boolean|null\n"
        "prefer_decentralization_method: string|null (候选值: harmonic, azimuth_equalization, agc)\n"
        "confidence: number (0~1)\n"
        "reason: string"
    )
    user_prompt = {
        "user_prompt": request.user_prompt,
        "artifact_tags": request.artifact_tags,
        "noise_level": request.noise_level,
        "has_depth_meta": request.has_depth_meta,
        "prefer_speed": request.prefer_speed,
        "prefer_quality": request.prefer_quality,
        "domain_context": request.domain_context,
        "tools": tool_payload,
    }
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
    ]


def build_llm_chat_messages(
    *,
    system_prompt: str,
    history: list[dict[str, str]],
    user_message: str,
    recommendation_summary: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    if recommendation_summary:
        messages.append(
            {
                "role": "system",
                "content": "推荐摘要（可引用）："
                + json.dumps(recommendation_summary, ensure_ascii=False),
            }
        )
    messages.append({"role": "user", "content": user_message})
    return messages
