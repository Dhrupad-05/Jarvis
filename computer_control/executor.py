from __future__ import annotations

import time
from dataclasses import dataclass

from computer_control.models import ActionPlan, ActionType, ExecutionReport, ResolvedTarget, TargetType
from computer_control.resolvers.applications import ApplicationExecutor, ApplicationResolver
from computer_control.resolvers.filesystem import FilesystemExecutor, FilesystemResolver
from computer_control.resolvers.websites import WebsiteResolver
from core.audit import log_action
from core.config import Settings
from tools.browser.controller import BrowserController


@dataclass(slots=True)
class ComputerControlService:
    settings: Settings
    app_resolver: ApplicationResolver
    app_executor: ApplicationExecutor
    website_resolver: WebsiteResolver
    browser: BrowserController
    filesystem_resolver: FilesystemResolver
    filesystem_executor: FilesystemExecutor

    @classmethod
    def from_settings(cls, settings: Settings) -> "ComputerControlService":
        return cls(
            settings=settings,
            app_resolver=ApplicationResolver.defaults(),
            app_executor=ApplicationExecutor(),
            website_resolver=WebsiteResolver(),
            browser=BrowserController(settings),
            filesystem_resolver=FilesystemResolver(settings.project_root),
            filesystem_executor=FilesystemExecutor(),
        )

    def execute(self, plan: ActionPlan) -> ExecutionReport:
        start = time.perf_counter()
        target: ResolvedTarget | None = None
        try:
            target = self._resolve(plan)
            if target is None:
                return self._report(False, "I could not resolve that target.", plan, None, start)
            success, verification = self._execute_resolved(plan, target)
            message = self._message(plan, target, success)
            report = self._report(success, message, plan, target, start, verification=verification)
            log_action(
                "computer_control",
                "success" if success else "failed",
                intent=plan.action.value,
                target=plan.target_text,
                target_type=target.target_type.value,
                strategy=target.strategy.value,
                execution_method=plan.preferred_executor or target.target_type.value,
                duration_ms=report.duration_ms,
                verification=verification,
            )
            return report
        except Exception as exc:
            report = self._report(False, f"Failed to execute request: {exc}", plan, target, start, error=str(exc))
            log_action("computer_control", "failed", intent=plan.action.value, target=plan.target_text, error=str(exc), duration_ms=report.duration_ms)
            return report

    def _resolve(self, plan: ActionPlan) -> ResolvedTarget | None:
        if plan.target_type is TargetType.FOLDER:
            return self.filesystem_resolver.resolve(plan) or self.website_resolver.resolve(plan)
        if plan.action is ActionType.SEARCH or plan.target_type is TargetType.WEBSITE:
            return self.website_resolver.resolve(plan)
        folder = self.filesystem_resolver.resolve(plan)
        if folder is not None:
            return folder
        app = self.app_resolver.resolve(plan.target_text)
        if app.confidence >= 0.7:
            return app
        website = self._maybe_website(plan)
        return website or app

    def _maybe_website(self, plan: ActionPlan) -> ResolvedTarget | None:
        lowered = plan.target_text.lower().strip()
        if lowered.startswith(("http://", "https://", "www.")):
            return self.website_resolver.resolve(plan)
        if " " not in lowered and len(lowered) > 1:
            return self.website_resolver.resolve(plan)
        return None

    def _execute_resolved(self, plan: ActionPlan, target: ResolvedTarget) -> tuple[bool, str | None]:
        if target.target_type is TargetType.WEBSITE:
            self.browser.open_url(str(target.value))
            return True, "Browser accepted URL."
        if target.target_type is TargetType.FOLDER:
            success = self.filesystem_executor.open(target)
            return success, "Folder exists and was opened." if success else "Folder does not exist."
        if target.target_type is TargetType.APPLICATION:
            if plan.action is ActionType.CLOSE:
                success = self.app_executor.close(str(target.metadata.get("process_hint") or target.name))
                return success, "Process close command succeeded." if success else "Process was not found."
            if plan.action is ActionType.STATUS:
                running = self.app_executor.is_running(str(target.metadata.get("process_hint") or target.name))
                if running is None:
                    return False, "No process hint available."
                return True, "Process is running." if running else "Process is not running."
            launched = self.app_executor.open(target)
            running = self.app_executor.is_running(target.metadata.get("process_hint"))
            if running is False and target.strategy.value not in {"shell_execution", "windows_search"}:
                return False, "Launch command ran, but process was not detected."
            return launched, "Launch command issued; process verification unavailable." if running is None else "Process detected." if running else "Process not detected."
        return False, "Unsupported target type."

    def _message(self, plan: ActionPlan, target: ResolvedTarget, success: bool) -> str:
        if not success:
            return f"I could not {plan.action.value} {plan.target_text}."
        if plan.action is ActionType.SEARCH:
            return f"Searched {target.name} for '{plan.query}'."
        if target.target_type is TargetType.WEBSITE:
            return f"Opened {target.name}."
        if plan.action is ActionType.CLOSE:
            return f"Closed {target.name}."
        if plan.action is ActionType.STATUS:
            return f"Checked {target.name}."
        return f"Opened {target.name}."

    def _report(
        self,
        success: bool,
        message: str,
        plan: ActionPlan,
        target: ResolvedTarget | None,
        start: float,
        *,
        verification: str | None = None,
        error: str | None = None,
    ) -> ExecutionReport:
        return ExecutionReport(
            success=success,
            message=message,
            plan=plan,
            target=target,
            duration_ms=(time.perf_counter() - start) * 1000,
            verification=verification,
            error=error,
        )
