from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from memory.memory_models import MemoryRecord, utc_now
from memory.memory_types import MemoryType


class MemoryStore(Protocol):
    def add(self, record: MemoryRecord) -> MemoryRecord: ...
    def get(self, memory_id: int) -> MemoryRecord | None: ...
    def list(self, limit: int = 50) -> list[MemoryRecord]: ...
    def update(self, memory_id: int, content: str, importance: int | None = None) -> MemoryRecord | None: ...
    def delete(self, memory_id: int) -> bool: ...
    def search(self, query: str, limit: int = 10, memory_types: tuple[MemoryType, ...] = ()) -> list[MemoryRecord]: ...


@dataclass(slots=True)
class SQLiteMemoryStore:
    db_path: Path

    def __post_init__(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def initialize(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance INTEGER NOT NULL,
                    tags TEXT NOT NULL,
                    source TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(memory_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_updated ON memories(updated_at)")

    def add(self, record: MemoryRecord) -> MemoryRecord:
        now = utc_now()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO memories(memory_type, content, importance, tags, source, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.memory_type.value,
                    record.content,
                    record.importance,
                    json.dumps(list(record.tags)),
                    record.source,
                    json.dumps(record.metadata),
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            return MemoryRecord(
                id=int(cursor.lastrowid),
                memory_type=record.memory_type,
                content=record.content,
                importance=record.importance,
                tags=record.tags,
                source=record.source,
                metadata=record.metadata,
                created_at=now,
                updated_at=now,
            )

    def get(self, memory_id: int) -> MemoryRecord | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        return self._row_to_record(row) if row else None

    def list(self, limit: int = 50) -> list[MemoryRecord]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM memories ORDER BY importance DESC, updated_at DESC LIMIT ?", (limit,)).fetchall()
        return [self._row_to_record(row) for row in rows]

    def update(self, memory_id: int, content: str, importance: int | None = None) -> MemoryRecord | None:
        existing = self.get(memory_id)
        if existing is None:
            return None
        new_importance = existing.importance if importance is None else importance
        now = utc_now().isoformat()
        with self._connect() as conn:
            conn.execute(
                "UPDATE memories SET content = ?, importance = ?, updated_at = ? WHERE id = ?",
                (content, new_importance, now, memory_id),
            )
        return self.get(memory_id)

    def delete(self, memory_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            return cursor.rowcount > 0

    def search(self, query: str, limit: int = 10, memory_types: tuple[MemoryType, ...] = ()) -> list[MemoryRecord]:
        terms = [f"%{term.lower()}%" for term in query.split() if term.strip()]
        type_values = tuple(memory_type.value for memory_type in memory_types)
        clauses: list[str] = []
        params: list[object] = []
        if terms:
            clauses.append("(" + " OR ".join("lower(content) LIKE ?" for _ in terms) + ")")
            params.extend(terms)
        if type_values:
            clauses.append("(" + " OR ".join("memory_type = ?" for _ in type_values) + ")")
            params.extend(type_values)
        where = "WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM memories {where} ORDER BY importance DESC, updated_at DESC LIMIT ?",
                params,
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_record(self, row: sqlite3.Row) -> MemoryRecord:
        return MemoryRecord(
            id=int(row["id"]),
            memory_type=MemoryType(row["memory_type"]),
            content=str(row["content"]),
            importance=int(row["importance"]),
            tags=tuple(json.loads(row["tags"])),
            source=str(row["source"]),
            metadata=json.loads(row["metadata"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )
