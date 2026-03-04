# apps/python-service

用途
- FastAPI 计算与可视化服务。

内容
- python_service/: 应用代码包。
- requirements.txt: 依赖列表。
- Dockerfile: 容器构建。

说明
- Uvicorn 入口为 python_service.app:app。
- 依赖 packages/compute 中的算法与 packages/geo-core 中的算法/Agent 模块。
- 默认端口为 8000。
- 数据增强接口：POST `/api/augmentation/run`（stick-and-pull 去伪影）。
- Agent 接口：
  - POST `/api/agent/chat`（聊天 + 可选图像上传 + 自动执行算法）
  - POST `/api/agent/recommend`
  - GET `/api/agent/tools`
  - GET `/api/agent/runtime`（在线/离线状态 + 模型 + 日志路径）
- 可选 LLM 配置文件：
  - 复制 `.env.agent.example` 为 `.env.agent.local` 并填写参数。
  - 服务启动时会自动加载该文件，因此仍可通过 `start.bat` 一键启动。
- LLM 调用日志：
  - 默认路径：`apps/python-service/logs/agent_llm_calls.jsonl`
  - 可通过 `GEO_AGENT_LLM_LOG_PATH` 自定义
