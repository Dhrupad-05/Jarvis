from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from coding.project_context import FileSummary, RepositorySummary


LANGUAGES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".md": "Markdown",
    ".json": "JSON",
    ".toml": "TOML",
    ".yaml": "YAML",
    ".yml": "YAML",
}

IGNORED_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", "dist", "build"}
IMPORTANT_NAMES = {"pyproject.toml", "requirements.txt", "package.json", "README.md", "app.py"}


@dataclass(frozen=True, slots=True)
class RepositoryIndexer:
    max_files: int = 500

    def index(self, root: Path) -> RepositorySummary:
        resolved = root.resolve()
        files: list[FileSummary] = []
        important: list[Path] = []
        dependencies: list[str] = []
        for path in self._iter_files(resolved):
            rel = path.relative_to(resolved)
            language = LANGUAGES.get(path.suffix.lower(), "Text")
            score = self._score(rel)
            summary = FileSummary(path=rel, language=language, size_bytes=path.stat().st_size, score=score)
            files.append(summary)
            if path.name in IMPORTANT_NAMES:
                important.append(rel)
                dependencies.extend(self._dependencies_from(path))
            if len(files) >= self.max_files:
                break
        files.sort(key=lambda item: item.score, reverse=True)
        return RepositorySummary(root=resolved, files=tuple(files), dependencies=tuple(dict.fromkeys(dependencies)), important_files=tuple(important))

    def relevant_files(self, root: Path, query: str, limit: int = 8) -> list[FileSummary]:
        summary = self.index(root)
        terms = {term.lower() for term in query.split() if len(term) > 2}
        scored: list[FileSummary] = []
        for file in summary.files:
            haystack = str(file.path).lower()
            score = file.score + sum(5 for term in terms if term in haystack)
            scored.append(FileSummary(file.path, file.language, file.size_bytes, score))
        return sorted(scored, key=lambda item: item.score, reverse=True)[:limit]

    def _iter_files(self, root: Path):
        for path in root.rglob("*"):
            if any(part in IGNORED_DIRS for part in path.parts):
                continue
            if path.is_file():
                yield path

    def _score(self, path: Path) -> float:
        score = 0.0
        if path.name in IMPORTANT_NAMES:
            score += 20
        if path.suffix.lower() in {".py", ".ts", ".tsx", ".js"}:
            score += 10
        if len(path.parts) <= 2:
            score += 3
        return score

    def _dependencies_from(self, path: Path) -> list[str]:
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []
        deps: list[str] = []
        if path.name == "requirements.txt":
            deps.extend(line.strip() for line in text.splitlines() if line.strip() and not line.startswith("#"))
        if path.name == "pyproject.toml":
            for line in text.splitlines():
                if ">=" in line or "==" in line:
                    deps.append(line.strip().strip('",'))
        if path.name == "package.json":
            deps.append("package.json present")
        return deps[:50]
