# python_service/api

计算与 ATV Agent 的 HTTP 路由层。

## 文件说明

- `borehole.py`：钻孔椭圆度计算/可视化/进度接口。
- `stressinv.py`：地应力反演接口。
- `augmentation.py`：旧版 stick-and-pull 增强接口。
- `agent.py`：ATV 专家 Agent（聊天、推荐、上传图像自动执行算法、结果下载）。
  - 新增 `/agent/runtime` 用于查看 LLM 在线状态和日志路径。

## Agent 执行链路

`POST /agent/chat` 支持文本 + 可选图像上传。  
上传图像时会自动：

1. 根据提示词推荐去伪影 pipeline。
2. 调用 `packages/geo-core/algorithms` 中算法执行。
3. 返回预览图与可下载结果文件。

若本轮未重新上传图像，可传 `reuse_session_id` 复用上一次 Agent 执行会话中的图像。
