from __future__ import annotations

from dataclasses import dataclass

from memory.memory_models import MemoryRecord


@dataclass(frozen=True, slots=True)
class MemorySummarizer:
    max_chars: int = 1_200

    def summarize(self, records: list[MemoryRecord]) -> str:
        lines: list[str] = []
        total = 0
        for record in records:
            line = f"- {record.memory_type.value}: {record.content}"
            if total + len(line) > self.max_chars:
                break
            lines.append(line)
            total += len(line)
        return "\n".join(lines) if lines else "No memory found."
