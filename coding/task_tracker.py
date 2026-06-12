from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class CodingTaskTracker:
    tasks: list[str] = field(default_factory=list)

    def add(self, task: str) -> None:
        self.tasks.append(task.strip())

    def list(self) -> tuple[str, ...]:
        return tuple(self.tasks)
