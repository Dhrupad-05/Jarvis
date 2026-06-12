from __future__ import annotations

from dataclasses import dataclass

from memory.memory_models import MemoryQuery, MemorySearchResult
from memory.memory_store import MemoryStore


@dataclass(slots=True)
class MemoryRetriever:
    store: MemoryStore

    def retrieve(self, query: MemoryQuery) -> list[MemorySearchResult]:
        records = self.store.search(query.text, limit=query.limit, memory_types=query.memory_types)
        results = [MemorySearchResult(record=record, score=self._score(query.text, record.content, record.importance)) for record in records]
        return sorted(results, key=lambda result: result.score, reverse=True)

    def select_context(self, query: MemoryQuery) -> str:
        selected: list[str] = []
        total = 0
        for result in self.retrieve(query):
            line = f"[{result.record.memory_type.value}#{result.record.id}] {result.record.content}"
            if total + len(line) > query.max_chars:
                break
            selected.append(line)
            total += len(line)
        return "\n".join(selected)

    def _score(self, query: str, content: str, importance: int) -> float:
        terms = {term.lower() for term in query.split() if term.strip()}
        if not terms:
            return float(importance)
        content_lower = content.lower()
        overlap = sum(1 for term in terms if term in content_lower)
        return overlap * 10.0 + importance
