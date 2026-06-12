from __future__ import annotations

from dataclasses import dataclass

from memory.memory_models import MemoryQuery, MemoryRecord
from memory.memory_retriever import MemoryRetriever
from memory.memory_types import MemoryType


@dataclass(slots=True)
class MemoryQueryEngine:
    retriever: MemoryRetriever

    def query(self, text: str, *, limit: int = 5, max_chars: int = 1_500) -> list[MemoryRecord]:
        memory_types = self._type_filter(text)
        results = self.retriever.retrieve(MemoryQuery(text=text, memory_types=memory_types, limit=limit, max_chars=max_chars))
        if not results and memory_types:
            results = self.retriever.retrieve(MemoryQuery(text=text, limit=limit, max_chars=max_chars))
        return [result.record for result in results]

    def _type_filter(self, text: str) -> tuple[MemoryType, ...]:
        lowered = text.lower()
        if any(word in lowered for word in ("favorite", "preference", "prefer")):
            return (MemoryType.PREFERENCE,)
        if "project" in lowered:
            return (MemoryType.PROJECT, MemoryType.CODING_CONTEXT)
        if "goal" in lowered:
            return (MemoryType.GOAL,)
        if any(word in lowered for word in ("task", "todo")):
            return (MemoryType.TASK,)
        if any(word in lowered for word in ("code", "repo", "architecture", "bug")):
            return (MemoryType.CODING_CONTEXT,)
        return ()
