from __future__ import annotations

from pathlib import Path

from brain.session import ChatSession
from computer_control.executor import ComputerControlService
from computer_control.models import ActionPlan, ActionType, ResolvedTarget, TargetType
from computer_control.resolvers.applications import ApplicationExecutor, ApplicationResolver
from computer_control.resolvers.filesystem import FilesystemExecutor, FilesystemResolver
from computer_control.resolvers.websites import WebsiteResolver
from core.config import Settings
from modes.mode_manager import ModeManager
from router.router import RequestRouter
from security.permissions import PermissionPolicy
from tools.browser.controller import BrowserController
from tools.registry import build_default_registry
from voice.diagnostics import run_voice_diagnostics
from voice.voice_manager import VoiceManager


class FakeLLM:
    def stream_chat(self, messages, system_prompt):
        yield "ok"


class FakeBrowser(BrowserController):
    def open_url(self, url: str) -> bool:
        return True


class ExistingProcessExecutor(ApplicationExecutor):
    def open(self, target: ResolvedTarget) -> bool:
        return True

    def process_ids(self, process_hint: str | None) -> set[int]:
        return {123}


class ExplodingRecorder:
    def record_push_to_talk(self, seconds: float = 5.0) -> Path:
        raise RuntimeError("device missing")


class FakeTranscriber:
    def transcribe(self, audio_path: Path) -> str:
        return "unused"


class FakeSpeaker:
    def speak(self, text: str) -> None:
        return None


def settings_for(tmp_path: Path, env: str = "") -> Settings:
    (tmp_path / ".env").write_text(env, encoding="utf-8")
    return Settings.load(project_root=tmp_path)


def session_for(settings: Settings) -> ChatSession:
    modes = ModeManager.from_settings(settings)
    registry = build_default_registry(settings=settings, mode_manager=modes, permission_policy=PermissionPolicy())
    return ChatSession(settings, FakeLLM(), RequestRouter(registry, modes), modes)


def test_voice_diagnostics_reports_missing_runtime_dependencies(tmp_path: Path) -> None:
    settings = settings_for(tmp_path, "ENABLE_VOICE=true\nENABLE_TTS=true\n")
    diagnostics = run_voice_diagnostics(settings)
    messages = "\n".join(diagnostics.messages())
    assert "sounddevice" in messages or diagnostics.sounddevice_available
    assert "faster-whisper" in messages or diagnostics.faster_whisper_available
    assert "PIPER_VOICE" in messages


def test_voice_listen_wraps_unexpected_errors(tmp_path: Path) -> None:
    settings = settings_for(tmp_path, "ENABLE_VOICE=true\n")
    manager = VoiceManager(
        settings=settings,
        session=session_for(settings),
        recorder=ExplodingRecorder(),
        transcriber=FakeTranscriber(),
        speaker=FakeSpeaker(),
        permission_policy=PermissionPolicy(),
    )
    try:
        manager.listen()
    except Exception as exc:
        assert "Voice listening failed" in str(exc)
    else:
        raise AssertionError("listen should fail safely")


def test_camera_resolves_to_application_not_random_website(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    service = ComputerControlService(
        settings=settings,
        app_resolver=ApplicationResolver.defaults(),
        app_executor=ExistingProcessExecutor(),
        website_resolver=WebsiteResolver(),
        browser=FakeBrowser(),
        filesystem_resolver=FilesystemResolver(tmp_path),
        filesystem_executor=FilesystemExecutor(),
    )
    report = service.execute(ActionPlan(ActionType.OPEN, "camera", TargetType.UNKNOWN, "open camera"))
    assert report.success
    assert report.target is not None
    assert report.target.target_type is TargetType.APPLICATION


def test_already_running_application_verifies_as_success(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    service = ComputerControlService(
        settings=settings,
        app_resolver=ApplicationResolver.defaults(),
        app_executor=ExistingProcessExecutor(),
        website_resolver=WebsiteResolver(),
        browser=FakeBrowser(),
        filesystem_resolver=FilesystemResolver(tmp_path),
        filesystem_executor=FilesystemExecutor(),
    )
    report = service.execute(ActionPlan(ActionType.OPEN, "powershell", TargetType.UNKNOWN, "open powershell"))
    assert report.success
    assert "Process is running" in (report.verification or "")
