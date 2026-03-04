from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class LLMError(RuntimeError):
    """Raised when the LLM request or response cannot be used."""


@dataclass(frozen=True)
class LLMConfig:
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: str = "qwen3.5-plus"
    api_key: str | None = None
    timeout_sec: float = 60.0
    temperature: float = 0.2
    max_tokens: int = 700
    log_enabled: bool = True
    log_path: str | None = None

    @property
    def is_enabled(self) -> bool:
        key = (self.api_key or "").strip()
        if not key:
            return False
        if key.lower() in {"your_api_key_here", "your-api-key-here", "change_me"}:
            return False
        return True

    @classmethod
    def from_env(cls) -> "LLMConfig":
        timeout_raw = os.getenv("GEO_AGENT_LLM_TIMEOUT_SEC", "60")
        max_tokens_raw = os.getenv("GEO_AGENT_LLM_MAX_TOKENS", "700")
        temperature_raw = os.getenv("GEO_AGENT_LLM_TEMPERATURE", "0.2")
        log_enabled_raw = os.getenv("GEO_AGENT_LLM_LOG_ENABLED", "true")
        try:
            timeout = float(timeout_raw)
        except ValueError:
            timeout = 60.0
        try:
            max_tokens = int(max_tokens_raw)
        except ValueError:
            max_tokens = 700
        try:
            temperature = float(temperature_raw)
        except ValueError:
            temperature = 0.2
        log_enabled = log_enabled_raw.strip().lower() in {"1", "true", "yes", "on"}
        log_path = os.getenv("GEO_AGENT_LLM_LOG_PATH", "").strip() or _default_llm_log_path()
        return cls(
            base_url=os.getenv(
                "GEO_AGENT_LLM_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ).rstrip("/"),
            model=os.getenv("GEO_AGENT_LLM_MODEL", "qwen3.5-plus"),
            api_key=(
                os.getenv("GEO_AGENT_LLM_API_KEY")
                or os.getenv("DASHSCOPE_API_KEY")
                or os.getenv("OPENAI_API_KEY")
            ),
            timeout_sec=timeout,
            temperature=temperature,
            max_tokens=max_tokens,
            log_enabled=log_enabled,
            log_path=log_path,
        )


class DashScopeCompatibleClient:
    """Minimal OpenAI-compatible Chat Completions client."""

    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig.from_env()

    @property
    def is_enabled(self) -> bool:
        return self.config.is_enabled

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        purpose: str | None = None,
    ) -> str:
        if not self.config.api_key:
            raise LLMError("LLM api key is missing. Set GEO_AGENT_LLM_API_KEY.")

        used_temperature = self.config.temperature if temperature is None else temperature
        used_max_tokens = self.config.max_tokens if max_tokens is None else max_tokens
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": used_temperature,
            "max_tokens": used_max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.config.base_url}/chat/completions"
        req = urllib.request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout_sec) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            if len(body) > 500:
                body = body[:500] + "..."
            self._append_log(
                {
                    "event": "llm_error",
                    "purpose": purpose or "chat",
                    "status_code": exc.code,
                    "error": f"LLM error {exc.code}: {body}",
                    "messages": messages,
                    "model": self.config.model,
                    "base_url": self.config.base_url,
                    "temperature": used_temperature,
                    "max_tokens": used_max_tokens,
                }
            )
            raise LLMError(f"LLM error {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            self._append_log(
                {
                    "event": "llm_error",
                    "purpose": purpose or "chat",
                    "error": f"LLM request failed: {exc.reason}",
                    "messages": messages,
                    "model": self.config.model,
                    "base_url": self.config.base_url,
                    "temperature": used_temperature,
                    "max_tokens": used_max_tokens,
                }
            )
            raise LLMError(f"LLM request failed: {exc.reason}") from exc
        except TimeoutError as exc:
            self._append_log(
                {
                    "event": "llm_error",
                    "purpose": purpose or "chat",
                    "error": "LLM request timed out.",
                    "messages": messages,
                    "model": self.config.model,
                    "base_url": self.config.base_url,
                    "temperature": used_temperature,
                    "max_tokens": used_max_tokens,
                }
            )
            raise LLMError("LLM request timed out.") from exc

        try:
            data = json.loads(body)
        except json.JSONDecodeError as exc:
            self._append_log(
                {
                    "event": "llm_error",
                    "purpose": purpose or "chat",
                    "error": "LLM response is not valid JSON payload.",
                    "response_preview": body[:1200],
                    "messages": messages,
                    "model": self.config.model,
                    "base_url": self.config.base_url,
                    "temperature": used_temperature,
                    "max_tokens": used_max_tokens,
                }
            )
            raise LLMError("LLM response is not valid JSON payload.") from exc
        text = _extract_text(data)
        self._append_log(
            {
                "event": "llm_success",
                "purpose": purpose or "chat",
                "messages": messages,
                "response_text": text,
                "model": self.config.model,
                "base_url": self.config.base_url,
                "temperature": used_temperature,
                "max_tokens": used_max_tokens,
            }
        )
        return text

    def runtime_status(self) -> dict[str, Any]:
        return {
            "llm_enabled": self.is_enabled,
            "api_key_present": bool((self.config.api_key or "").strip()),
            "model": self.config.model,
            "base_url": self.config.base_url,
            "timeout_sec": self.config.timeout_sec,
            "log_enabled": self.config.log_enabled,
            "log_path": self.config.log_path,
        }

    def _append_log(self, payload: dict[str, Any]) -> None:
        if not self.config.log_enabled:
            return
        if not self.config.log_path:
            return
        try:
            path = Path(self.config.log_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            item = {
                "ts": datetime.utcnow().isoformat() + "Z",
                **payload,
            }
            with path.open("a", encoding="utf-8") as file:
                file.write(json.dumps(item, ensure_ascii=False) + "\n")
        except Exception:
            # Log writing should never break normal agent behavior.
            return


def _extract_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LLMError("LLM response missing choices.")
    message = choices[0].get("message", {})
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                chunks.append(str(item.get("text", "")))
        text = "".join(chunks).strip()
        if text:
            return text
    raise LLMError("LLM response content is empty.")


def _default_llm_log_path() -> str:
    repo_root = Path(__file__).resolve().parents[5]
    return str(repo_root / "apps" / "python-service" / "logs" / "agent_llm_calls.jsonl")
