# tools

Tool registry exposed to the ATV agent.

Current state:

- Active tools are auto-generated from `AlgorithmRegistry`.
- Planned tools are explicitly registered for future ATV scenarios:
  - `atv.fracture_pick.v1`
  - `atv.collapse_detect.v1`

Add new tools in `registry.py` to keep agent capability growth explicit and auditable.
