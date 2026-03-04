# agents

`agents/` provides an ATV expert layer on top of algorithm registry:

- Prompt-based artifact-removal recommendation (`stick_pull`, `decentralization`).
- Chat assistant behavior for ATV workflows.
- Extensible tool registry for future ATV tasks (fracture picking, collapse detection, etc.).

## Structure

- `contracts.py`: API contracts for recommend/chat/tools.
- `service.py`: orchestration service with LLM + rules fallback.
- `policy/`: deterministic selector policies.
- `llm/`: DashScope compatible client, prompt templates, parser.
- `tools/`: tool registry exposed to the agent.

## Runtime

Agent endpoints are wired in `algorithms/api/routes_agent.py`.

If LLM env vars are not configured, the agent still works via rule-based strategy.
