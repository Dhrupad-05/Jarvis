from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from brain.session import ChatSession
from core.config import Settings
from memory.memory_manager import MemoryManager
from memory.memory_types import MemoryType
from modes.mode_manager import ModeManager
from router.router import RequestRouter
from security.permissions import PermissionPolicy
from tools.registry import build_default_registry


class FakeLLM:
    def stream_chat(self, messages, system_prompt):
        yield "llm fallback"


def settings_for(tmp_path: Path) -> Settings:
    (tmp_path / ".env").write_text("MEMORY_DB_NAME=memory_test.sqlite3\n", encoding="utf-8")
    return Settings.load(project_root=tmp_path)


def session_for(settings: Settings) -> ChatSession:
    modes = ModeManager.from_settings(settings)
    registry = build_default_registry(settings=settings, mode_manager=modes, permission_policy=PermissionPolicy())
    return ChatSession(settings, FakeLLM(), RequestRouter(registry, modes), modes)


def test_natural_memory_question_survives_restart(tmp_path: Path) -> None:
    first = session_for(settings_for(tmp_path))
    assert "Remembered memory" in "".join(first.handle_stream("remember My test phrase is banana rocket 947"))

    second = session_for(settings_for(tmp_path))
    output = "".join(second.handle_stream("What is my test phrase?"))
    assert "banana rocket 947" in output
    assert output != "llm fallback"


def test_project_lookup_returns_relevant_project_quickly(tmp_path: Path) -> None:
    session = session_for(settings_for(tmp_path))
    for text in (
        "remember Project Alpha uses FastAPI.",
        "remember Project Beta uses Django.",
        "remember Project Gamma uses Flask.",
    ):
        assert "Remembered memory" in "".join(session.handle_stream(text))

    start = time.perf_counter()
    output = "".join(session.handle_stream("Which project uses Django?"))
    elapsed = time.perf_counter() - start
    assert elapsed < 2.0
    assert "Project Beta uses Django" in output


def test_large_memory_collection_is_bounded(tmp_path: Path) -> None:
    manager = MemoryManager.from_settings(settings_for(tmp_path))
    for index in range(250):
        manager.remember(f"Project {index} uses library {index}", memory_type=MemoryType.PROJECT)
    context = manager.retrieve_context("library 249", limit=5, max_chars=500)
    assert "library 249" in context
    assert len(context) <= 500


def test_memory_developer_commands(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    session = session_for(settings)
    assert "Remembered memory" in "".join(session.handle_stream("remember Project Delta uses SQLite."))
    tool = session.router.tool_registry.get("memory")
    assert "total" in tool.developer_command("stats").message  # type: ignore[attr-defined]
    assert "Project Delta" in tool.developer_command("search SQLite").message  # type: ignore[attr-defined]
    assert "Project Delta" in tool.developer_command("export").message  # type: ignore[attr-defined]


def test_cli_memory_restart_validation(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    env_file = root / ".env"
    original = env_file.read_text(encoding="utf-8") if env_file.exists() else None
    try:
        env_file.write_text("MEMORY_DB_NAME=cli_memory_test.sqlite3\n", encoding="utf-8")
        db = root / "data" / "cli_memory_test.sqlite3"
        if db.exists():
            db.unlink()
        remember = subprocess.run(
            [sys.executable, "app.py", "--once", "remember My test phrase is banana rocket 947"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        recall = subprocess.run(
            [sys.executable, "app.py", "--once", "What is my test phrase?"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert remember.returncode == 0
        assert recall.returncode == 0
        assert "banana rocket 947" in recall.stdout
    finally:
        if original is None:
            env_file.unlink(missing_ok=True)
        else:
            env_file.write_text(original, encoding="utf-8")
        (root / "data" / "cli_memory_test.sqlite3").unlink(missing_ok=True)
        (root / "data" / "cli_memory_test.sqlite3-wal").unlink(missing_ok=True)
        (root / "data" / "cli_memory_test.sqlite3-shm").unlink(missing_ok=True)
