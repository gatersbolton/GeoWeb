# policy

Policy layer for algorithm routing.

- `selector_rules.py`: production-safe baseline policy.
  - Parses user prompt keywords.
  - Scores registered algorithms using capability metadata.
  - Generates pipeline/config recommendations with decision log.
- `selector_ml.py`: placeholder for future ML policy.

Design rule: keep policy independent from low-level algorithm implementation details.
