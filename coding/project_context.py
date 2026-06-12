from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True, slots=True)
class FileSummary:
    path: Path
    language: str
    size_bytes: int
    score: float = 0.0


@dataclass(frozen=True, slots=True)
class RepositorySummary:
    root: Path
    files: tuple[FileSummary, ...]
    dependencies: tuple[str, ...] = ()
    important_files: tuple[Path, ...] = ()
    notes: tuple[str, ...] = ()

    def compact(self, max_files: int = 20) -> str:
        lines = [f"Repository: {self.root}"]
        if self.dependencies:
            lines.append("Dependencies: " + ", ".join(self.dependencies[:20]))
        if self.important_files:
            lines.append("Important files: " + ", ".join(str(path) for path in self.important_files[:10]))
        for file in self.files[:max_files]:
            lines.append(f"- {file.path} [{file.language}, {file.size_bytes} bytes]")
        return "\n".join(lines)


@dataclass(slots=True)
class ProjectContext:
    active_root: Path | None = None
    summaries: dict[Path, RepositorySummary] = field(default_factory=dict)

    def set_active(self, root: Path, summary: RepositorySummary) -> None:
        self.active_root = root
        self.summaries[root] = summary

    def current_summary(self) -> RepositorySummary | None:
        if self.active_root is None:
            return None
        return self.summaries.get(self.active_root)
