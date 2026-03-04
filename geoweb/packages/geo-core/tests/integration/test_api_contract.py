from algorithms.api.routes_algorithms import get_algorithms
from algorithms.api.routes_agent import agent_chat, agent_recommend, list_agent_tools
from algorithms.api.routes_jobs import create_job, get_job, get_job_result
from algorithms.api.schemas import AgentChatRequestSchema, AgentRecommendRequestSchema, JobCreateRequest


def test_get_algorithms_returns_registered_items() -> None:
    payload = get_algorithms()
    algo_ids = {item.algo_id for item in payload}
    assert "artifact.stick_pull.v1" in algo_ids
    assert "artifact.decentralization.v1" in algo_ids
    assert "enhancement.super_resolution.v1" in algo_ids


def test_jobs_lifecycle_output_contract() -> None:
    created = create_job(
        JobCreateRequest(
            frame={
                "data": [[1, 2], [3, 4]],
                "source_meta": {"well_id": "W-1", "input_format": "npy"},
            }
        )
    )
    state = get_job(created.job_id)
    assert state.status.value == "SUCCEEDED"

    result = get_job_result(created.job_id)
    assert result.result_data is not None
    assert len(result.result_data) == 2
    assert len(result.result_data[0]) == 2


def test_agent_recommend_returns_pipeline() -> None:
    response = agent_recommend(
        AgentRecommendRequestSchema(
            user_prompt="请做 stick pull 去伪影，然后增强清晰度",
            artifact_tags=["stick_pull"],
            noise_level=0.2,
            has_depth_meta=True,
        )
    )
    assert response.recommended_pipeline[0] == "artifact.stick_pull.v1"
    assert len(response.candidates) >= 1


def test_agent_chat_returns_answer_and_optional_recommendation() -> None:
    response = agent_chat(
        AgentChatRequestSchema(
            message="帮我推荐去伪影算法，重点是去除偏心伪影。",
        )
    )
    assert isinstance(response.answer, str)
    assert len(response.answer) > 0
    assert response.recommendation is not None
    assert "artifact.decentralization.v1" in response.recommendation.recommended_pipeline


def test_agent_tools_contains_planned_atv_capabilities() -> None:
    tools = list_agent_tools()
    tool_ids = {item.tool_id for item in tools}
    assert "algo:artifact.stick_pull.v1" in tool_ids
    assert "atv.fracture_pick.v1" in tool_ids
