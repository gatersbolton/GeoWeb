# packages/geo-core

Purpose
- Core ATV processing framework, including artifact-removal algorithms and agent orchestration.

Contents
- `algorithms/`
  - `artifacts/`: artifact removal algorithms (`stick_pull`, `decentralization`)
  - `enhancement/`: enhancement algorithms (`super_resolution`)
  - `agents/`: ATV expert agent (recommend + chat + extensible tool registry)
  - `api/`: FastAPI routes for jobs/algorithms/agent
- `configs/env/`
  - `agent.env.example`: LLM runtime env template (DashScope/Qwen)
- `tests/`
  - integration and unit tests for framework + agent behavior

Notes
- Agent can run without online LLM key (rule-based fallback).
- Keep logic language-agnostic when possible.
