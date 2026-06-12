from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from coding.code_explainer import CodeExplainer
from coding.error_analyzer import ErrorAnalysis, ErrorAnalyzer
from coding.project_context import ProjectContext, RepositorySummary
from coding.repository_indexer import RepositoryIndexer
from coding.task_tracker import CodingTaskTracker
from memory.memory_manager import MemoryManager
from memory.memory_types import MemoryType


@dataclass(slots=True)
class CodingManager:
    memory: MemoryManager
    indexer: RepositoryIndexer = field(default_factory=RepositoryIndexer)
    context: ProjectContext = field(default_factory=ProjectContext)
    errors: ErrorAnalyzer = field(default_factory=ErrorAnalyzer)
    explainer: CodeExplainer = field(default_factory=CodeExplainer)
    tasks: CodingTaskTracker = field(default_factory=CodingTaskTracker)

    def index_repository(self, root: Path) -> RepositorySummary:
        summary = self.indexer.index(root)
        self.context.set_active(root.resolve(), summary)
        self.memory.remember(
            f"Repository indexed: {summary.root} with {len(summary.files)} files.",
            memory_type=MemoryType.CODING_CONTEXT,
            source="coding_assistant",
        )
        return summary

    def repository_context(self, root: Path, query: str, max_chars: int = 2_000) -> str:
        relevant = self.indexer.relevant_files(root, query)
        lines = [f"- {file.path} [{file.language}, {file.size_bytes} bytes]" for file in relevant]
        text = "\n".join(lines)
        return text[:max_chars]

    def analyze_error(self, error_text: str) -> ErrorAnalysis:
        analysis = self.errors.analyze(error_text)
        self.memory.remember(
            f"Error analyzed: {analysis.language} {analysis.error_type} - {analysis.likely_cause}",
            memory_type=MemoryType.CODING_CONTEXT,
            source="coding_assistant",
        )
        return analysis

    def explain_code(self, code: str) -> str:
        return self.explainer.explain_snippet(code)

    def track_task(self, task: str) -> None:
        self.tasks.add(task)
        self.memory.remember(f"Coding task: {task}", memory_type=MemoryType.TASK, source="coding_assistant")
