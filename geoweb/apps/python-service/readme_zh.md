# apps/python-service

用途
- FastAPI 计算与可视化服务。

内容
- python_service/: 应用代码包。
- requirements.txt: 依赖列表。
- Dockerfile: 容器构建。

说明
- Uvicorn 入口为 python_service.app:app。
- 依赖 packages/compute 中的算法与 packages/geo-core 中的伪影示例。
- 默认端口为 8000。
- 数据增强接口：POST `/api/augmentation/run`（stick-and-pull 去伪影）。
