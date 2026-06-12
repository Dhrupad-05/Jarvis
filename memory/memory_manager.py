from __future__ import annotations

from dataclasses import dataclass

from core.audit import log_action
from core.config import Settings
from memory.memory_models import MemoryQuery, MemoryRecord
from memory.memory_retriever import MemoryRetriever
from memory.memory_store import MemoryStore, SQLiteMemoryStore
from memory.memory_summarizer import MemorySummarizer
from memory.memory_types import MemoryType
from modes.modes import AssistantMode


@dataclass(slots=True)
class MemoryManager:
    store: MemoryStore
    retriever: MemoryRetriever
    summarizer: MemorySummarizer

    @classmethod
    def from_settings(cls, settings: Settings) -> "MemoryManager":
        store = SQLiteMemoryStore(settings.memory_db_path)
        return cls(store=store, retriever=MemoryRetriever(store), summarizer=MemorySummarizer())

    def remember(
        self,
        content: str,
        *,
        memory_type: MemoryType = MemoryType.GENERAL_NOTE,
        importance: int = 3,
        tags: tuple[str, ...] = (),
        source: str = "user",
        mode: AssistantMode | None = None,
    ) -> MemoryRecord | None:
        if mode is not None and mode.name.lower() == "interview" and source != "explicit_user_memory":
            log_action("memory_store", "skipped", reason="interview_mode", chars=len(content))
            return None
        record = self.store.add(
            MemoryRecord(
                id=None,
                memory_type=memory_type,
                content=content.strip(),
                importance=max(1, min(5, importance)),
                tags=tags,
                source=source,
            )
        )
        log_action("memory_store", "success", id=record.id, type=record.memory_type.value, chars=len(content))
        return record

    def retrieve_context(self, text: str, *, limit: int = 5, max_chars: int = 2_000) -> str:
        return self.retriever.select_context(MemoryQuery(text=text, limit=limit, max_chars=max_chars))

    def search(self, text: str, *, limit: int = 10) -> list[MemoryRecord]:
        return [result.record for result in self.retriever.retrieve(MemoryQuery(text=text, limit=limit))]

    def update(self, memory_id: int, content: str, importance: int | None = None) -> MemoryRecord | None:
        record = self.store.update(memory_id, content.strip(), importance=importance)
        log_action("memory_update", "success" if record else "not_found", id=memory_id)
        return record

    def delete(self, memory_id: int) -> bool:
        deleted = self.store.delete(memory_id)
        log_action("memory_delete", "success" if deleted else "not_found", id=memory_id)
        return deleted

    def summarize(self, limit: int = 20) -> str:
        return self.summarizer.summarize(self.store.list(limit=limit))

    def stats(self) -> dict[str, int]:
        counts: dict[str, int] = {"total": self.store.count()}
        for record in self.store.export():
            counts[record.memory_type.value] = counts.get(record.memory_type.value, 0) + 1
        return counts

    def export_text(self) -> str:
        records = self.store.export()
        if not records:
            return "No memory found."
        return "\n".join(f"#{record.id} [{record.memory_type.value}] {record.content}" for record in records)
