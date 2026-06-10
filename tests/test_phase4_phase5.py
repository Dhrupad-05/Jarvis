from __future__ import annotations

from pathlib import Path

from brain.session import ChatSession
from core.config import Settings
from modes.mode_manager import ModeManager
from router.router import RequestRouter
from security.permissions import PermissionPolicy
from tools.registry import build_default_registry
from voice.voice_manager import VoiceManager


class FakeLLM:
    def stream_chat(self, messages, system_prompt):
        yield "ok"


class FakeRecorder:
    def record_push_to_talk(self, seconds: float = 5.0) -> Path:
        return Path("fake.wav")


class FakeTranscriber:
    def transcribe(self, audio_path: Path) -> str:
        return "hello from voice"


class FakeSpeaker:
    def __init__(self) -> None:
        self.spoken: list[str] = []

    def speak(self, text: str) -> None:
        self.spoken.append(text)


def make_session(tmp_path: Path, mode: str = "productivity") -> ChatSession:
    (tmp_path / ".env").write_text(f"DEFAULT_MODE={mode}\n", encoding="utf-8")
    settings = Settings.load(project_root=tmp_path)
    modes = ModeManager.from_settings(settings)
    registry = build_default_registry(settings=settings, mode_manager=modes, permission_policy=PermissionPolicy())
    return ChatSession(settings, FakeLLM(), RequestRouter(registry, modes), modes)


def test_file_create_folder_is_low_risk(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    output = "".join(session.handle_stream('create folder "notes"'))
    assert "Created folder" in output
    assert (tmp_path / "notes").exists()


def test_delete_requires_confirmation(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    target = tmp_path / "delete-me.txt"
    target.write_text("x", encoding="utf-8")
    output = "".join(session.handle_stream('delete "delete-me.txt"'))
    assert "requires confirmation" in output.lower()
    assert target.exists()


def test_confirmed_delete_executes(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    target = tmp_path / "delete-me.txt"
    target.write_text("x", encoding="utf-8")
    output = "".join(session.handle_stream('delete "delete-me.txt" --confirm'))
    assert "Deleted" in output
    assert not target.exists()


def test_interview_mode_blocks_automation(tmp_path: Path) -> None:
    session = make_session(tmp_path, mode="interview")
    output = "".join(session.handle_stream('create folder "blocked"'))
    assert "Interview mode disables files" in output
    assert not (tmp_path / "blocked").exists()


def test_voice_manager_listen_uses_adapters(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    speaker = FakeSpeaker()
    manager = VoiceManager(
        settings=session.settings,
        session=session,
        recorder=FakeRecorder(),
        transcriber=FakeTranscriber(),
        speaker=speaker,
        permission_policy=PermissionPolicy(),
    )
    assert manager.listen() == "hello from voice"
    manager.speak("answer")
    assert speaker.spoken == ["answer"]


def test_interview_mode_blocks_voice(tmp_path: Path) -> None:
    session = make_session(tmp_path, mode="interview")
    manager = VoiceManager(
        settings=session.settings,
        session=session,
        recorder=FakeRecorder(),
        transcriber=FakeTranscriber(),
        speaker=FakeSpeaker(),
        permission_policy=PermissionPolicy(),
    )
    try:
        manager.listen()
    except Exception as exc:
        assert "Interview mode disables voice" in str(exc)
    else:
        raise AssertionError("Interview mode should block voice listening")
