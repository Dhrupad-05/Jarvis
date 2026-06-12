from __future__ import annotations

from dataclasses import dataclass
import re

from memory.memory_models import MemoryQuery, MemorySearchResult
from memory.memory_store import MemoryStore


@dataclass(slots=True)
class MemoryRetriever:
    store: MemoryStore
    stopwords: frozenset[str] = frozenset(
        {
            "a",
            "an",
            "and",
            "are",
            "do",
            "does",
            "for",
            "is",
            "me",
            "my",
            "of",
            "on",
            "the",
            "to",
            "what",
            "which",
            "who",
            "why",
            "uses",
            "use",
            "about",
        }
    )

    def retrieve(self, query: MemoryQuery) -> list[MemorySearchResult]:
        clean_query = " ".join(self._terms(query.text))
        records = self.store.search(clean_query or query.text, limit=min(query.limit * 4, 50), memory_types=query.memory_types)
        results = [MemorySearchResult(record=record, score=self._score(query.text, record.content, record.importance)) for record in records]
        return sorted(results, key=lambda result: result.score, reverse=True)[: query.limit]

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
        terms = set(self._terms(query))
        if not terms:
            return float(importance)
        content_lower = content.lower()
        overlap = sum(1 for term in terms if term in content_lower)
        exact_bonus = 5.0 if query.lower().strip(" ?.") in content_lower else 0.0
        return overlap * 10.0 + exact_bonus + importance

    def _terms(self, text: str) -> list[str]:
        terms = re.findall(r"[a-zA-Z0-9_+-]+", text.lower())
        return [term for term in terms if len(term) > 1 and term not in self.stopwords]
