from __future__ import annotations

from pathlib import Path

from brain.session import ChatSession
from core.config import Settings
from memory.memory_manager import MemoryManager
from memory.memory_models import MemoryQuery
from memory.memory_types import MemoryType
from modes.mode_manager import ModeManager
from router.router import RequestRouter
from security.permissions import PermissionPolicy
from tools.registry import build_default_registry


class FakeLLM:
    def stream_chat(self, messages, system_prompt):
        yield "ok"


def settings_for(tmp_path: Path, mode: str = "productivity") -> Settings:
    (tmp_path / ".env").write_text(f"DEFAULT_MODE={mode}\nMEMORY_DB_NAME=test_memory.sqlite3\n", encoding="utf-8")
    return Settings.load(project_root=tmp_path)


def test_memory_create_retrieve_update_delete(tmp_path: Path) -> None:
    manager = MemoryManager.from_settings(settings_for(tmp_path))
    record = manager.remember("I prefer concise answers", memory_type=MemoryType.PREFERENCE)
    assert record is not None
    assert record.id is not None
    assert manager.search("concise")[0].id == record.id
    updated = manager.update(record.id, "I prefer concise technical answers", importance=5)
    assert updated is not None
    assert updated.importance == 5
    assert manager.delete(record.id)
    assert manager.search("concise") == []


def test_sqlite_persistence(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    first = MemoryManager.from_settings(settings)
    record = first.remember("Project Atlas is important", memory_type=MemoryType.PROJECT)
    assert record is not None
    second = MemoryManager.from_settings(settings)
    assert second.search("Atlas")[0].content == "Project Atlas is important"


def test_token_aware_context_selection(tmp_path: Path) -> None:
    manager = MemoryManager.from_settings(settings_for(tmp_path))
    manager.remember("alpha " * 100, memory_type=MemoryType.GENERAL_NOTE)
    manager.remember("beta short", memory_type=MemoryType.GENERAL_NOTE)
    context = manager.retriever.select_context(MemoryQuery(text="alpha beta", limit=10, max_chars=80))
    assert len(context) <= 80


def test_memory_summary(tmp_path: Path) -> None:
    manager = MemoryManager.from_settings(settings_for(tmp_path))
    manager.remember("Goal: finish reliability hardening", memory_type=MemoryType.GOAL)
    assert "finish reliability" in manager.summarize()


def test_memory_tool_router_integration(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    modes = ModeManager.from_settings(settings)
    registry = build_default_registry(settings=settings, mode_manager=modes, permission_policy=PermissionPolicy())
    router = RequestRouter(registry, modes)
    session = ChatSession(settings, FakeLLM(), router, modes)
    assert "Remembered memory" in "".join(session.handle_stream("remember I like local-first systems"))
    output = "".join(session.handle_stream("recall local-first"))
    assert "local-first systems" in output


def test_interview_mode_policy_skips_implicit_memory(tmp_path: Path) -> None:
    settings = settings_for(tmp_path, mode="interview")
    modes = ModeManager.from_settings(settings)
    manager = MemoryManager.from_settings(settings)
    record = manager.remember("implicit observation", mode=modes.active_mode, source="assistant")
    assert record is None


def test_explicit_memory_allowed_in_interview_mode(tmp_path: Path) -> None:
    settings = settings_for(tmp_path, mode="interview")
    modes = ModeManager.from_settings(settings)
    manager = MemoryManager.from_settings(settings)
    record = manager.remember("explicit note", mode=modes.active_mode, source="explicit_user_memory")
    assert record is not None


def test_memory_store_type_filter(tmp_path: Path) -> None:
    manager = MemoryManager.from_settings(settings_for(tmp_path))
    manager.remember("coding repo uses Python", memory_type=MemoryType.CODING_CONTEXT)
    manager.remember("I prefer tea", memory_type=MemoryType.PREFERENCE)
    records = manager.store.search("prefer coding Python tea", memory_types=(MemoryType.CODING_CONTEXT,))
    assert len(records) == 1
    assert records[0].memory_type is MemoryType.CODING_CONTEXT
