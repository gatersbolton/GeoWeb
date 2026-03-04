# apps/python-service/python_service

用途
- FastAPI 服务源码。

内容
- app.py: 应用启动与路由注册。
- api/: 接口路由（椭圆度、反演、增强、Agent）。
- services/: 异步任务与进度汇报。
- thirdparty/: 科研代码封装。
- core/: 路径解析与进度状态。

说明
- core/paths.py 维护仓库相对路径。
- app.py 会自动加载 Agent 的本地环境配置文件（可选）：
  - `apps/python-service/.env.agent.local`
  - `packages/geo-core/configs/env/agent.env.local`
