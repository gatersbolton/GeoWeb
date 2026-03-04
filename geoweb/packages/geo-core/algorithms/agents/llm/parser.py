from __future__ import annotations

import json


def extract_json_object(content: str) -> dict:
    text = (content or "").strip()
    if not text:
        return {}

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    fenced = _extract_fenced_json(text)
    if fenced is not None:
        return fenced

    first = text.find("{")
    last = text.rfind("}")
    if first >= 0 and last > first:
        snippet = text[first : last + 1]
        try:
            parsed = json.loads(snippet)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    return {}


def _extract_fenced_json(text: str) -> dict | None:
    marker = "```"
    if marker not in text:
        return None
    start = text.find(marker)
    end = text.find(marker, start + len(marker))
    while start >= 0 and end > start:
        block = text[start + len(marker) : end].strip()
        if block.lower().startswith("json"):
            block = block[4:].strip()
        try:
            parsed = json.loads(block)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        start = text.find(marker, end + len(marker))
        end = text.find(marker, start + len(marker))
    return None
