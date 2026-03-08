# src/views

页面级 Vue 视图。

## 新增页面

- `AgentAssistant.vue`
  - ATV智脑页面，用于 ATV 图像处理与解释对话。
  - 支持对话、图像上传、推荐流程展示。
  - 支持 Markdown 渲染（表格/列表/代码块）。
  - 展示 `/api/agent/chat` 返回的处理预览图与下载链接。
  - 未重新上传时可复用上次图像会话，支持“这张图继续处理”。
