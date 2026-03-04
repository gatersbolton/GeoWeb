from __future__ import annotations

from algorithms.agents.contracts import AgentToolSpec
from algorithms.core.registry import AlgorithmRegistry


class AgentToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, AgentToolSpec] = {}

    def register(self, tool: AgentToolSpec) -> None:
        self._tools[tool.tool_id] = tool

    def list_tools(self) -> list[AgentToolSpec]:
        return [self._tools[key] for key in sorted(self._tools.keys())]

    def list_active_tools(self) -> list[AgentToolSpec]:
        return [tool for tool in self.list_tools() if tool.status == "active"]


def build_default_tool_registry(registry: AlgorithmRegistry) -> AgentToolRegistry:
    tool_registry = AgentToolRegistry()

    for descriptor in registry.list_descriptors():
        algo = descriptor.algorithm
        capability = descriptor.capability or {}
        handles = list(capability.get("handles_artifact_types", []))
        category = "artifact" if algo.algo_id.startswith("artifact.") else "enhancement"
        tool_registry.register(
            AgentToolSpec(
                tool_id=f"algo:{algo.algo_id}",
                display_name=algo.algo_id,
                category=category,
                description=_build_algorithm_description(algo.algo_id, capability),
                status="active",
                algo_id=algo.algo_id,
                handles=handles,
                metadata={
                    "version": algo.version,
                    "cost_profile": capability.get("cost_profile", {}),
                },
            )
        )

    # Planned ATV capabilities for future extensions.
    tool_registry.register(
        AgentToolSpec(
            tool_id="atv.fracture_pick.v1",
            display_name="fracture picking",
            category="analysis",
            description="裂隙拾取（规划接口，后续接入）",
            status="planned",
            handles=["fracture_picking"],
            metadata={"owner": "atv-agent"},
        )
    )
    tool_registry.register(
        AgentToolSpec(
            tool_id="atv.collapse_detect.v1",
            display_name="collapse detection",
            category="analysis",
            description="崩落识别（规划接口，后续接入）",
            status="planned",
            handles=["collapse_detection"],
            metadata={"owner": "atv-agent"},
        )
    )

    return tool_registry


def _build_algorithm_description(algo_id: str, capability: dict) -> str:
    handles = capability.get("handles_artifact_types", [])
    output_chars = capability.get("output_characteristics", {})
    edge = output_chars.get("edge_preservation", "unknown")
    if handles:
        return f"Supports {', '.join(handles)} artifact handling, edge_preservation={edge}."
    return f"General enhancement algorithm, edge_preservation={edge}."
