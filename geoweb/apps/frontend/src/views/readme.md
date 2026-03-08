# src/views

Page-level Vue views.

## New page

- `AgentAssistant.vue`
  - ATV智脑 page for conversational ATV image processing and interpretation.
  - Supports conversation, image upload, pipeline recommendation display.
  - Supports Markdown rendering (tables/lists/code blocks).
  - Shows processed preview image and download links from `/api/agent/chat`.
  - Reuses previous uploaded image session when user continues with "this image" style prompts.
