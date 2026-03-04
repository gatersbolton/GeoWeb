# python_service/api

HTTP routers for compute and ATV-agent capabilities.

## Endpoints

- `borehole.py`: borehole ellipticity compute/visualization/progress.
- `stressinv.py`: stress inversion compute/progress/download.
- `augmentation.py`: legacy stick-and-pull augmentation endpoint.
- `agent.py`: ATV expert agent chat/recommendation + file-driven algorithm execution.
  - Adds runtime endpoint `/agent/runtime` for LLM online status and log path.

## Agent Workflow

`POST /agent/chat` accepts text + optional uploaded image.  
If an image is uploaded, the service:

1. Asks agent policy/LLM to recommend pipeline.
2. Runs selected algorithms from `packages/geo-core/algorithms`.
3. Returns preview image and downloadable result files.

If no new image is uploaded, you can pass `reuse_session_id` to reuse the image from a previous
agent execution session.
