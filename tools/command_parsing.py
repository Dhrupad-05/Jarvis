from __future__ import annotations

import re
import shlex
from pathlib import Path


def has_confirmation(text: str) -> bool:
    lowered = text.lower()
    return "--confirm" in lowered or lowered.startswith("confirm ")


def strip_confirmation(text: str) -> str:
    return re.sub(r"\s*--confirm\s*", " ", text, flags=re.IGNORECASE).strip()


def quoted_or_tail(text: str, prefixes: tuple[str, ...]) -> str:
    cleaned = strip_confirmation(text)
    try:
        tokens = shlex.split(cleaned)
    except ValueError:
        tokens = cleaned.split()
    if len(tokens) >= 2 and " " in cleaned and '"' in cleaned:
        return tokens[-1]
    lowered = cleaned.lower()
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return cleaned[len(prefix) :].strip().strip('"')
    return cleaned.strip().strip('"')


def safe_path(root: Path, raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = root / path
    return path.resolve()
