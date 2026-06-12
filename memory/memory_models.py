from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from memory.memory_types import MemoryType


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    id: int | None
    memory_type: MemoryType
    content: str
    importance: int = 3
    tags: tuple[str, ...] = ()
    source: str = "user"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class MemoryQuery:
    text: str
    memory_types: tuple[MemoryType, ...] = ()
    limit: int = 5
    max_chars: int = 2_000


@dataclass(frozen=True, slots=True)
class MemorySearchResult:
    record: MemoryRecord
    score: float
