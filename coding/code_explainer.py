from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CodeExplainer:
    max_chars: int = 2_000

    def explain_snippet(self, code: str) -> str:
        snippet = code.strip()
        if len(snippet) > self.max_chars:
            snippet = snippet[: self.max_chars] + "\n..."
        lines = [line for line in snippet.splitlines() if line.strip()]
        return (
            f"Snippet has {len(lines)} non-empty lines. "
            "Read it by identifying inputs, state changes, branches, and returned values."
        )
