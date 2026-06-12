from __future__ import annotations

from pathlib import Path

from coding.coding_manager import CodingManager
from coding.error_analyzer import ErrorAnalyzer
from core.config import Settings
from memory.memory_manager import MemoryManager
from modes.mode_manager import ModeManager
from router.router import RequestRouter
from security.permissions import PermissionPolicy
from tools.registry import build_default_registry


def settings_for(tmp_path: Path) -> Settings:
    (tmp_path / ".env").write_text("MEMORY_DB_NAME=coding_memory.sqlite3\n", encoding="utf-8")
    return Settings.load(project_root=tmp_path)


def create_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "pyproject.toml").write_text('[project]\nname="demo"\ndependencies=["fastapi>=0.1"]\n', encoding="utf-8")
    (repo / "app.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")
    (repo / "README.md").write_text("# Demo\n", encoding="utf-8")
    ignored = repo / ".venv"
    ignored.mkdir()
    (ignored / "ignored.py").write_text("x = 1\n", encoding="utf-8")
    return repo


def test_repository_indexing_skips_ignored_dirs(tmp_path: Path) -> None:
    manager = CodingManager(MemoryManager.from_settings(settings_for(tmp_path)))
    repo = create_repo(tmp_path)
    summary = manager.index_repository(repo)
    paths = {str(file.path) for file in summary.files}
    assert "app.py" in paths
    assert ".venv\\ignored.py" not in paths
    assert summary.important_files


def test_repository_context_is_bounded(tmp_path: Path) -> None:
    manager = CodingManager(MemoryManager.from_settings(settings_for(tmp_path)))
    repo = create_repo(tmp_path)
    context = manager.repository_context(repo, "fastapi app", max_chars=80)
    assert len(context) <= 80
    assert "app.py" in context


def test_error_analysis_python_traceback() -> None:
    analysis = ErrorAnalyzer().analyze("Traceback\nModuleNotFoundError: No module named 'x'")
    assert analysis.language == "Python"
    assert analysis.error_type == "ModuleNotFoundError"


def test_coding_manager_writes_project_memory(tmp_path: Path) -> None:
    memory = MemoryManager.from_settings(settings_for(tmp_path))
    manager = CodingManager(memory)
    manager.track_task("refactor router")
    assert "refactor router" in memory.search("refactor router")[0].content


def test_coding_tool_router_integration(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    repo = create_repo(tmp_path)
    modes = ModeManager.from_settings(settings)
    registry = build_default_registry(settings=settings, mode_manager=modes, permission_policy=PermissionPolicy())
    router = RequestRouter(registry, modes)
    decision = router.route(f'analyze repo "{repo}"')
    assert decision.tool_name == "coding"
    result = registry.execute("coding", f'analyze repo "{repo}"')
    assert result.success
    assert "Repository:" in result.message


def test_coding_task_routes_to_coding_not_memory(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    modes = ModeManager.from_settings(settings)
    registry = build_default_registry(settings=settings, mode_manager=modes, permission_policy=PermissionPolicy())
    router = RequestRouter(registry, modes)
    decision = router.route("coding task inspect memory architecture")
    assert decision.tool_name == "coding"
    result = registry.execute("coding", "coding task inspect memory architecture")
    assert result.success
    recall = registry.execute("memory", "recall memory architecture")
    assert "inspect memory architecture" in recall.message


def test_coding_tool_error_analysis(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    modes = ModeManager.from_settings(settings)
    registry = build_default_registry(settings=settings, mode_manager=modes, permission_policy=PermissionPolicy())
    result = registry.execute("coding", "explain error Traceback TypeError: bad operand")
    assert result.success
    assert "TypeError" in result.message
