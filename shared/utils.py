from __future__ import annotations

from collections.abc import Iterable


def normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def bounded_join(parts: Iterable[str], separator: str = "\n", max_chars: int = 8_000) -> str:
    output: list[str] = []
    total = 0
    for part in parts:
        if total + len(part) > max_chars:
            break
        output.append(part)
        total += len(part) + len(separator)
    return separator.join(output)

