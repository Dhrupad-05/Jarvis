from __future__ import annotations

from pathlib import Path

from computer_control.executor import ComputerControlService
from computer_control.models import ActionPlan, ActionType, ResolutionStrategy, ResolvedTarget, TargetType
from computer_control.planner import ActionPlanner
from computer_control.resolvers.applications import ApplicationCandidate, ApplicationExecutor, ApplicationResolver
from computer_control.resolvers.filesystem import FilesystemExecutor, FilesystemResolver
from computer_control.resolvers.websites import WebsiteResolver
from core.config import Settings
from modes.mode_manager import ModeManager
from router.router import RequestRouter
from security.permissions import PermissionPolicy
from tools.browser.controller import BrowserController
from tools.browser.tool import BrowserTool
from tools.registry import build_default_registry


class FakeBrowser(BrowserController):
    def __init__(self) -> None:
        self.urls: list[str] = []

    def open_url(self, url: str) -> None:
        self.urls.append(url)


class FailingApplicationExecutor(ApplicationExecutor):
    def open(self, target: ResolvedTarget) -> bool:
        return True

    def is_running(self, process_hint: str | None) -> bool | None:
        return False


def settings_for(tmp_path: Path, mode: str = "productivity") -> Settings:
    (tmp_path / ".env").write_text(f"DEFAULT_MODE={mode}\n", encoding="utf-8")
    return Settings.load(project_root=tmp_path)


def test_query_extraction_variants() -> None:
    planner = ActionPlanner()
    assert planner.plan("search google for machine learning").query == "machine learning"
    assert planner.plan("search for python decorators").query == "python decorators"
    assert planner.plan("google transformers tutorial").query == "transformers tutorial"
    assert planner.plan("find information about vector databases").query == "vector databases"
    youtube = planner.plan("search youtube for llm engineering")
    assert youtube.target_text == "youtube"
    assert youtube.query == "llm engineering"


def test_registry_google_search_uses_robust_query_parser(tmp_path: Path) -> None:
    result = BrowserTool(controller=FakeBrowser()).execute("search google for machine learning")
    assert result.data["url"].endswith("q=machine+learning")
    assert "for machine learning" not in result.message


def test_website_domain_resolution_is_generic() -> None:
    resolver = WebsiteResolver()
    plan = ActionPlan(ActionType.OPEN, "linkedin", TargetType.UNKNOWN, "open linkedin")
    target = resolver.resolve(plan)
    assert target is not None
    assert target.value == "https://www.linkedin.com"
    assert target.strategy is ResolutionStrategy.DOMAIN_HEURISTIC


def test_irregular_website_resolution() -> None:
    resolver = WebsiteResolver()
    plan = ActionPlan(ActionType.OPEN, "huggingface", TargetType.UNKNOWN, "open huggingface")
    target = resolver.resolve(plan)
    assert target is not None
    assert target.value == "https://huggingface.co"


def test_start_menu_application_discovery(tmp_path: Path, monkeypatch) -> None:
    start = tmp_path / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    start.mkdir(parents=True)
    shortcut = start / "Brave Browser.lnk"
    shortcut.write_text("", encoding="utf-8")
    monkeypatch.setenv("ProgramData", str(tmp_path))
    monkeypatch.setenv("AppData", str(tmp_path / "missing"))
    target = ApplicationResolver.defaults().resolve("brave")
    assert target.strategy is ResolutionStrategy.START_MENU
    assert target.value == shortcut


def test_path_application_discovery(tmp_path: Path, monkeypatch) -> None:
    exe = tmp_path / "cursor.exe"
    exe.write_text("", encoding="utf-8")
    monkeypatch.setenv("PATH", str(tmp_path))
    target = ApplicationResolver.defaults().resolve("cursor")
    assert target.strategy is ResolutionStrategy.PATH_EXECUTABLE
    assert str(target.value[0]).lower() == str(exe).lower()


def test_execution_verification_failure(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    app_resolver = ApplicationResolver.defaults()
    app_resolver.known_commands["fakeapp"] = ApplicationCandidate(
        "FakeApp",
        ("fakeapp",),
        ResolutionStrategy.KNOWN_REGISTRY,
        "fakeapp",
        0.95,
    )
    service = ComputerControlService(
        settings=settings,
        app_resolver=app_resolver,
        app_executor=FailingApplicationExecutor(),
        website_resolver=WebsiteResolver(),
        browser=FakeBrowser(),
        filesystem_resolver=FilesystemResolver(tmp_path),
        filesystem_executor=FilesystemExecutor(),
    )
    report = service.execute(ActionPlan(ActionType.OPEN, "fakeapp", TargetType.UNKNOWN, "open fakeapp"))
    assert not report.success
    assert report.verification == "Launch command ran, but process was not detected."


def test_control_tool_fallback_routes_unknown_website(tmp_path: Path) -> None:
    settings = settings_for(tmp_path)
    modes = ModeManager.from_settings(settings)
    registry = build_default_registry(settings=settings, mode_manager=modes, permission_policy=PermissionPolicy())
    router = RequestRouter(registry, modes)
    decision = router.route("open kaggle")
    assert decision.tool_name == "computer_control"


def test_interview_mode_blocks_control_fallback(tmp_path: Path) -> None:
    settings = settings_for(tmp_path, mode="interview")
    modes = ModeManager.from_settings(settings)
    registry = build_default_registry(settings=settings, mode_manager=modes, permission_policy=PermissionPolicy())
    result = registry.execute("computer_control", "open linkedin")
    assert not result.success
    assert "Interview mode disables browser" in result.message
