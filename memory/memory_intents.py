from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from memory.memory_types import MemoryType


class MemoryIntentType(str, Enum):
    STORE = "store"
    QUERY = "query"
    DELETE = "delete"
    SUMMARY = "summary"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class MemoryIntent:
    intent_type: MemoryIntentType
    content: str
    memory_type: MemoryType = MemoryType.GENERAL_NOTE
    confidence: float = 0.0
    reason: str = ""


class MemoryIntentClassifier:
    """Deterministic memory intent layer for local, token-free capture."""

    STORE_PATTERNS: tuple[tuple[re.Pattern[str], MemoryType, str], ...] = (
        (re.compile(r"^(?:remember|store|save|note|don't forget|do not forget)\s+(?P<content>.+)$", re.I), MemoryType.GENERAL_NOTE, "explicit_store"),
        (re.compile(r"^(?:important note|note to self)\s*:?\s*(?P<content>.+)$", re.I), MemoryType.GENERAL_NOTE, "important_note"),
        (re.compile(r"^(?:my\s+)?(?:preference|preferred .+)\s+(?:is|are)\s+(?P<content>.+)$", re.I), MemoryType.PREFERENCE, "preference"),
        (re.compile(r"^my favorite (?P<subject>[\w\s-]+?)\s+is\s+(?P<value>.+)$", re.I), MemoryType.PREFERENCE, "favorite"),
        (re.compile(r"^i (?:prefer|like|use|work with)\s+(?P<content>.+)$", re.I), MemoryType.PREFERENCE, "user_preference"),
        (re.compile(r"^my goal\s+(?:is|for .+ is)\s+(?P<content>.+)$", re.I), MemoryType.GOAL, "goal"),
        (re.compile(r"^my project\s+(?:is|uses|called)\s+(?P<content>.+)$", re.I), MemoryType.PROJECT, "project"),
        (re.compile(r"^(?P<content>project\s+[\w -]+\s+uses\s+.+)$", re.I), MemoryType.PROJECT, "project_fact"),
        (re.compile(r"^(?:task|todo)\s*:?\s*(?P<content>.+)$", re.I), MemoryType.TASK, "task"),
        (re.compile(r"^(?:i learned|learning note)\s*:?\s*(?P<content>.+)$", re.I), MemoryType.LEARNING_NOTE, "learning_note"),
        (re.compile(r"^(?:coding context|repo note|architecture decision)\s*:?\s*(?P<content>.+)$", re.I), MemoryType.CODING_CONTEXT, "coding_context"),
    )
    QUERY_PATTERNS: tuple[re.Pattern[str], ...] = (
        re.compile(r"^(?:what|which|who|when|where|tell me|show me|list|recall|search memory|what do you remember)\b", re.I),
        re.compile(r"\b(?:favorite|preference|prefer|goal|project|remember about)\b", re.I),
    )

    def classify(self, text: str) -> MemoryIntent:
        cleaned = " ".join(text.strip().split())
        lowered = cleaned.lower()
        if not cleaned:
            return MemoryIntent(MemoryIntentType.NONE, "", confidence=0.0, reason="empty")
        if lowered.startswith(("forget memory", "delete memory")):
            return MemoryIntent(MemoryIntentType.DELETE, cleaned, confidence=0.95, reason="delete")
        if lowered.startswith(("summarize memory", "what do you remember")):
            return MemoryIntent(MemoryIntentType.SUMMARY, cleaned, confidence=0.95, reason="summary")
        for pattern, memory_type, reason in self.STORE_PATTERNS:
            match = pattern.match(cleaned)
            if not match:
                continue
            content = self._content_from(match, cleaned)
            if reason == "explicit_store":
                memory_type = self.infer_type(content)
            return MemoryIntent(MemoryIntentType.STORE, content, memory_type, 0.92, reason)
        if any(pattern.search(cleaned) for pattern in self.QUERY_PATTERNS):
            return MemoryIntent(MemoryIntentType.QUERY, cleaned, confidence=0.78, reason="query")
        return MemoryIntent(MemoryIntentType.NONE, cleaned, confidence=0.0, reason="no_match")

    def _content_from(self, match: re.Match[str], original: str) -> str:
        groups = match.groupdict()
        if "subject" in groups and "value" in groups:
            return f"My favorite {groups['subject'].strip()} is {groups['value'].strip()}"
        return (groups.get("content") or original).strip()

    def infer_type(self, content: str) -> MemoryType:
        lowered = content.lower()
        if "favorite" in lowered or "prefer" in lowered or "like" in lowered:
            return MemoryType.PREFERENCE
        if "project" in lowered:
            return MemoryType.PROJECT
        if "goal" in lowered:
            return MemoryType.GOAL
        if "task" in lowered or "todo" in lowered:
            return MemoryType.TASK
        if "learned" in lowered or "learning" in lowered:
            return MemoryType.LEARNING_NOTE
        if any(word in lowered for word in ("code", "repo", "architecture", "bug", "refactor")):
            return MemoryType.CODING_CONTEXT
        return MemoryType.GENERAL_NOTE
