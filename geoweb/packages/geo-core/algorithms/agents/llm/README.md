# llm

LLM integration utilities for the ATV agent.

- `client.py`: OpenAI-compatible chat client (DashScope compatible).
- `prompts.py`: system/user prompt builders.
- `parser.py`: robust JSON extraction from model output.

## Environment Variables

- `GEO_AGENT_LLM_BASE_URL` (default: `https://dashscope.aliyuncs.com/compatible-mode/v1`)
- `GEO_AGENT_LLM_MODEL` (default: `qwen3.5-plus`)
- `GEO_AGENT_LLM_API_KEY` (required for online model call)
- `GEO_AGENT_LLM_TIMEOUT_SEC` (default: `60`)
- `GEO_AGENT_LLM_MAX_TOKENS` (default: `700`)
- `GEO_AGENT_LLM_TEMPERATURE` (default: `0.2`)
- `GEO_AGENT_LLM_LOG_ENABLED` (default: `true`)
- `GEO_AGENT_LLM_LOG_PATH` (default: `apps/python-service/logs/agent_llm_calls.jsonl`)

Without `GEO_AGENT_LLM_API_KEY`, agent falls back to rule-based behavior.
