from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from brain.session import ChatSession
from core.config import Settings
from memory.memory_intents import MemoryIntentClassifier, MemoryIntentType
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
    (tmp_path / ".env").write_text("MEMORY_DB_NAME=phase62_memory.sqlite3\n", encoding="utf-8")
    return Settings.load(project_root=tmp_path)


def session_for(settings: Settings) -> ChatSession:
    modes = ModeManager.from_settings(settings)
    registry = build_default_registry(settings=settings, mode_manager=modes, permission_policy=PermissionPolicy())
    return ChatSession(settings, FakeLLM(), RequestRouter(registry, modes), modes)


def test_memory_intent_classifier_semantic_store_variants() -> None:
    classifier = MemoryIntentClassifier()
    samples = [
        "My favorite language is Python.",
        "My goal is become better at algorithms.",
        "Important note: exams start Monday.",
        "Project Beta uses Django.",
        "Don't forget I prefer short answers.",
    ]
    for sample in samples:
        intent = classifier.classify(sample)
        assert intent.intent_type is MemoryIntentType.STORE
        assert intent.confidence >= 0.7


def test_semantic_memory_capture_prevents_chat_fallback(tmp_path: Path) -> None:
    session = session_for(settings_for(tmp_path))
    output = "".join(session.handle_stream("My favorite language is Python."))
    assert "Remembered memory" in output
    answer = "".join(session.handle_stream("What is my favorite language?"))
    assert "Python" in answer
    assert answer != "llm fallback"


def test_multiple_preferences_store_and_retrieve(tmp_path: Path) -> None:
    session = session_for(settings_for(tmp_path))
    for line in (
        "My favorite language is Python.",
        "My favorite editor is VS Code.",
        "My favorite database is PostgreSQL.",
    ):
        assert "Remembered memory" in "".join(session.handle_stream(line))
    assert "Python" in "".join(session.handle_stream("What is my favorite language?"))
    assert "VS Code" in "".join(session.handle_stream("What is my favorite editor?"))
    assert "PostgreSQL" in "".join(session.handle_stream("What is my favorite database?"))


def test_semantic_memory_survives_restart(tmp_path: Path) -> None:
    first = session_for(settings_for(tmp_path))
    assert "Remembered memory" in "".join(first.handle_stream("My favorite language is Python."))
    second = session_for(settings_for(tmp_path))
    assert "Python" in "".join(second.handle_stream("What is my favorite language?"))


def test_project_query_returns_best_match_without_hanging(tmp_path: Path) -> None:
    session = session_for(settings_for(tmp_path))
    for line in ("Project Alpha uses FastAPI.", "Project Beta uses Django.", "Project Gamma uses Flask."):
        assert "Remembered memory" in "".join(session.handle_stream(line))
    start = time.perf_counter()
    answer = "".join(session.handle_stream("Which project uses Django?"))
    assert time.perf_counter() - start < 2.0
    assert "Project Beta uses Django" in answer
    assert "Project Alpha" not in answer


def test_large_memory_query_is_bounded_and_relevant(tmp_path: Path) -> None:
    manager = MemoryManager.from_settings(settings_for(tmp_path))
    for index in range(60):
        manager.remember(f"Project {index} uses framework {index}", memory_type=MemoryType.PROJECT)
    records = manager.search("What do you remember about my projects?", limit=5)
    assert len(records) <= 5
    assert all(record.memory_type is MemoryType.PROJECT for record in records)


def test_memory_show_developer_command(tmp_path: Path) -> None:
    session = session_for(settings_for(tmp_path))
    assert "Remembered memory #1" in "".join(session.handle_stream("My favorite database is PostgreSQL."))
    tool = session.router.tool_registry.get("memory")
    result = tool.developer_command("show 1")  # type: ignore[attr-defined]
    assert result.success
    assert "PostgreSQL" in result.message


def test_cli_semantic_memory_restart_validation(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    env_file = root / ".env"
    original = env_file.read_text(encoding="utf-8") if env_file.exists() else None
    db_names = ("phase62_cli.sqlite3", "phase62_cli.sqlite3-wal", "phase62_cli.sqlite3-shm")
    try:
        env_file.write_text("MEMORY_DB_NAME=phase62_cli.sqlite3\n", encoding="utf-8")
        for name in db_names:
            (root / "data" / name).unlink(missing_ok=True)
        store = subprocess.run(
            [sys.executable, "app.py", "--once", "My favorite language is Python."],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        recall = subprocess.run(
            [sys.executable, "app.py", "--once", "What is my favorite language?"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        assert store.returncode == 0
        assert recall.returncode == 0
        assert "Python" in recall.stdout
    finally:
        if original is None:
            env_file.unlink(missing_ok=True)
        else:
            env_file.write_text(original, encoding="utf-8")
        for name in db_names:
            (root / "data" / name).unlink(missing_ok=True)
