from __future__ import annotations

from pathlib import Path

from brain.session import ChatSession
from core.config import Settings
from modes.mode_manager import ModeManager
from router.intents import IntentType
from router.router import RequestRouter
from tools.registry import build_default_registry


class FakeLLM:
    def stream_chat(self, messages, system_prompt):
        yield "hello"


def test_settings_loads_and_creates_dirs(tmp_path: Path) -> None:
    settings = Settings.load(project_root=tmp_path)
    assert settings.data_dir.exists()
    assert settings.log_dir.exists()
    assert settings.main_model


def test_router_detects_tool() -> None:
    settings = Settings.load()
    router = RequestRouter(build_default_registry(), ModeManager.from_settings(settings))
    decision = router.route("Open Chrome")
    assert decision.intent.intent_type is IntentType.TOOL
    assert decision.tool_name == "applications"


def test_mode_switch_updates_session() -> None:
    settings = Settings.load()
    modes = ModeManager.from_settings(settings)
    session = ChatSession(settings, FakeLLM(), RequestRouter(build_default_registry(), modes), modes)
    output = "".join(session.handle_stream("switch to study mode"))
    assert "Switched to Study mode" in output
    assert session.mode_manager.active_mode_key == "study"


def test_chat_uses_llm_and_records_history() -> None:
    settings = Settings.load()
    modes = ModeManager.from_settings(settings)
    session = ChatSession(settings, FakeLLM(), RequestRouter(build_default_registry(), modes), modes)
    assert "".join(session.handle_stream("Explain transformers")) == "hello"
    assert len(session.state.messages) == 2
