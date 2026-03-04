# packages/geo-core

用途
- ATV 去伪影与智能分析核心框架。

内容
- `algorithms/`
  - `artifacts/`: 去伪影算法（`stick_pull`、`decentralization`）
  - `enhancement/`: 图像增强算法（`super_resolution`）
  - `agents/`: ATV 专家 Agent（推荐 + chat + 可扩展工具注册）
  - `api/`: FastAPI 接口（任务/算法/Agent）
- `configs/env/`
  - `agent.env.example`: DashScope/Qwen 配置模板
- `tests/`
  - 框架与 Agent 的单元/集成测试

说明
- 未配置 LLM Key 时，Agent 自动走规则降级策略。
- 尽量保持语言无关的实现。
