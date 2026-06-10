from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from typing import Protocol

from core.config import Settings
from core.exceptions import LLMError
from shared.models import Message


class LLMClient(Protocol):
    def stream_chat(self, messages: Sequence[Message], system_prompt: str) -> Iterator[str]:
        """Yield response text chunks for a chat request."""


@dataclass(slots=True)
class OllamaClient:
    """Ollama chat client using the local HTTP API."""

    settings: Settings
    timeout_seconds: int = 120

    def stream_chat(self, messages: Sequence[Message], system_prompt: str) -> Iterator[str]:
        payload = {
            "model": self.settings.main_model,
            "messages": [{"role": "system", "content": system_prompt}, *[m.to_ollama() for m in messages]],
            "stream": True,
        }
        request = urllib.request.Request(
            f"{self.settings.ollama_base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                yield from self._read_stream(response)
        except urllib.error.URLError as exc:
            raise LLMError(
                f"Cannot reach Ollama at {self.settings.ollama_base_url}. "
                "Start Ollama and ensure the configured model is available."
            ) from exc

    def _read_stream(self, response: Iterable[bytes]) -> Iterator[str]:
        for raw_line in response:
            if not raw_line:
                continue
            try:
                event = json.loads(raw_line.decode("utf-8"))
            except json.JSONDecodeError as exc:
                raise LLMError("Ollama returned an invalid streaming event") from exc
            if "error" in event:
                raise LLMError(str(event["error"]))
            content = event.get("message", {}).get("content")
            if content:
                yield str(content)
            if event.get("done"):
                break

