from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from brain.session import ChatSession
from computer_control.executor import ComputerControlService
from computer_control.models import ActionPlan, ActionType, ResolutionStrategy, ResolvedTarget, TargetType
from computer_control.resolvers.applications import ApplicationCandidate, ApplicationExecutor, ApplicationResolver
from computer_control.resolvers.filesystem import FilesystemExecutor, FilesystemResolver
from computer_control.resolvers.websites import WebsiteResolver
from core.config import Settings
from modes.mode_manager import ModeManager
from router.router import RequestRouter
from security.permissions import PermissionPolicy
from shared.responses import ToolResult
from tools.base_tool import BaseTool, ToolMetadata
from tools.browser.controller import BrowserController
from tools.control.tool import ComputerControlTool
from tools.registry import ToolRegistry, build_default_registry
from security.permissions import Capability, RiskLevel


class FakeLLM:
    def stream_chat(self, messages, system_prompt):
        yield "still alive"


class RecordingBrowser(BrowserController):
    def __init__(self, success: bool = True) -> None:
        self.success = success
        self.urls: list[str] = []

    def open_url(self, url: str) -> bool:
        self.urls.append(url)
        return self.success


class ExplodingTool(BaseTool):
    metadata = ToolMetadata(
        name="explode",
        description="Explodes for reliability tests",
        keywords=("explode",),
        capability=Capability.APPLICATIONS,
        risk_level=RiskLevel.LOW,
    )

    def execute(self, user_text: str, *, confirmed: bool = False) -> ToolResult:
        raise RuntimeError("boom")


def settings_for(tmp_path: Path, mode: str = "productivity") -> Settings:
    (tmp_path / ".env").write_text(f"DEFAULT_MODE={mode}\n", encoding="utf-8")
    return Settings.load(project_root=tmp_path)


def make_session(tmp_path: Path) -> ChatSession:
    settings = settings_for(tmp_path)
    modes = ModeManager.from_settings(settings)
    registry = build_default_registry(settings=settings, mode_manager=modes, permission_policy=PermissionPolicy())
    return ChatSession(settings, FakeLLM(), RequestRouter(registry, modes), modes)


def test_open_camera_requires_clarification_and_opens_nothing(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    browser = RecordingBrowser()
    service = ComputerControlService(
        settings=settings,
        app_resolver=ApplicationResolver.defaults(),
        app_executor=ApplicationExecutor(),
        website_resolver=WebsiteResolver(),
        browser=browser,
        filesystem_resolver=FilesystemResolver(tmp_path),
        filesystem_executor=FilesystemExecutor(),
    )
    report = service.execute(ActionPlan(ActionType.OPEN, "camera", TargetType.UNKNOWN, "open camera"))
    assert not report.success
    assert "not confident enough" in report.message
    assert browser.urls == []


def test_unknown_application_does_not_shell_execute(tmp_path: Path) -> None:
    session = make_session(tmp_path)
    output = "".join(session.handle_stream("open definitely-not-a-real-local-app"))
    assert "not confident enough" in output


def test_unknown_website_does_not_open_random_domain(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    browser = RecordingBrowser()
    tool = ComputerControlTool(
        settings=settings,
        service=ComputerControlService(
            settings=settings,
            app_resolver=ApplicationResolver.defaults(),
            app_executor=ApplicationExecutor(),
            website_resolver=WebsiteResolver(),
            browser=browser,
            filesystem_resolver=FilesystemResolver(tmp_path),
            filesystem_executor=FilesystemExecutor(),
        ),
    )
    result = tool.execute("open madeupwebthing")
    assert not result.success
    assert browser.urls == []


def test_failed_browser_launch_returns_failure(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    service = ComputerControlService(
        settings=settings,
        app_resolver=ApplicationResolver.defaults(),
        app_executor=ApplicationExecutor(),
        website_resolver=WebsiteResolver(),
        browser=RecordingBrowser(success=False),
        filesystem_resolver=FilesystemResolver(tmp_path),
        filesystem_executor=FilesystemExecutor(),
    )
    report = service.execute(ActionPlan(ActionType.OPEN, "openai", TargetType.UNKNOWN, "open openai"))
    assert not report.success
    assert report.verification == "Browser did not accept URL."


def test_verified_application_failure_reports_failure(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    app_resolver = ApplicationResolver.defaults()
    app_resolver.known_commands["fakeapp"] = ApplicationCandidate(
        "FakeApp",
        ("fakeapp",),
        ResolutionStrategy.KNOWN_REGISTRY,
        "fakeapp",
        0.95,
    )

    class NoProcessExecutor(ApplicationExecutor):
        def open(self, target: ResolvedTarget) -> bool:
            return True

        def process_ids(self, process_hint: str | None) -> set[int]:
            return set()

        def wait_for_running(self, process_hint: str | None, previous_pids: set[int], timeout_seconds: float = 4.0) -> bool | None:
            return False

    service = ComputerControlService(
        settings=settings,
        app_resolver=app_resolver,
        app_executor=NoProcessExecutor(),
        website_resolver=WebsiteResolver(),
        browser=RecordingBrowser(),
        filesystem_resolver=FilesystemResolver(tmp_path),
        filesystem_executor=FilesystemExecutor(),
    )
    report = service.execute(ActionPlan(ActionType.OPEN, "fakeapp", TargetType.UNKNOWN, "open fakeapp"))
    assert not report.success
    assert "process was not detected" in (report.verification or "")


def test_tool_exception_is_isolated(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    modes = ModeManager.from_settings(settings)
    registry = ToolRegistry(mode_manager=modes, permission_policy=PermissionPolicy())
    registry.register(ExplodingTool())
    result = registry.execute("explode", "explode")
    assert not result.success
    assert "failed safely" in result.message


def test_session_survives_tool_failure(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    modes = ModeManager.from_settings(settings)
    registry = ToolRegistry(mode_manager=modes, permission_policy=PermissionPolicy())
    registry.register(ExplodingTool())
    session = ChatSession(settings, FakeLLM(), RequestRouter(registry, modes), modes)
    first = "".join(session.handle_stream("explode"))
    second = "".join(session.handle_stream("hello"))
    assert "failed safely" in first
    assert second == "still alive"


def test_interactive_loop_continues_after_tool_failure(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "app.py"],
        input="open camera\n/exit\n",
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1],
        timeout=30,
        check=False,
    )
    assert result.returncode == 0
    assert "not confident enough" in result.stdout
    assert "Goodbye." in result.stdout
