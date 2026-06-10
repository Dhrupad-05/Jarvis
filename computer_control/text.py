from __future__ import annotations

import re


FILLER_PREFIXES = (
    "please ",
    "can you ",
    "could you ",
    "would you ",
    "jarvis ",
)


def clean_request(text: str) -> str:
    cleaned = " ".join(text.strip().split())
    lowered = cleaned.lower()
    for prefix in FILLER_PREFIXES:
        if lowered.startswith(prefix):
            return cleaned[len(prefix) :].strip()
    return cleaned


def normalize_target(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def title_name(text: str) -> str:
    known_upper = {"obs": "OBS", "vscode": "VS Code", "x": "X"}
    key = normalize_target(text)
    if key in known_upper:
        return known_upper[key]
    return " ".join(part.capitalize() for part in text.replace("_", " ").split())
