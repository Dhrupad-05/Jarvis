from __future__ import annotations

import time
from dataclasses import dataclass

from computer_control.models import ActionPlan, ActionType, ExecutionReport, ResolutionStrategy, ResolvedTarget, TargetType
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
        candidates: list[ResolvedTarget] = []
        try:
            candidates = self._candidates(plan)
            target = self._choose_candidate(plan, candidates)
            if target is None:
                report = self._report(False, self._clarification_message(plan, candidates), plan, None, start, candidates=candidates)
                log_action(
                    "computer_control_resolution",
                    "clarification_required",
                    intent=plan.action.value,
                    target=plan.target_text,
                    candidates=[self._candidate_log(candidate) for candidate in candidates],
                )
                return report
            success, verification = self._execute_resolved(plan, target)
            message = self._message(plan, target, success)
            report = self._report(success, message, plan, target, start, verification=verification, candidates=candidates)
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
                confidence=target.confidence,
                candidates=[self._candidate_log(candidate) for candidate in candidates],
            )
            return report
        except Exception as exc:
            report = self._report(False, f"Failed to execute request: {exc}", plan, target, start, error=str(exc), candidates=candidates)
            log_action("computer_control", "failed", intent=plan.action.value, target=plan.target_text, error=str(exc), duration_ms=report.duration_ms)
            return report

    def _candidates(self, plan: ActionPlan) -> list[ResolvedTarget]:
        if plan.target_type is TargetType.FOLDER:
            return [candidate for candidate in (self.filesystem_resolver.resolve(plan), self.website_resolver.resolve(plan)) if candidate is not None]
        if plan.action is ActionType.SEARCH or plan.target_type is TargetType.WEBSITE:
            website = self.website_resolver.resolve(plan)
            return [website] if website is not None else []
        candidates: list[ResolvedTarget] = []
        folder = self.filesystem_resolver.resolve(plan)
        if folder is not None:
            candidates.append(folder)
        app = self.app_resolver.resolve(plan.target_text)
        candidates.append(app)
        website = self._maybe_website(plan)
        if website is not None:
            candidates.append(website)
        return sorted(candidates, key=lambda candidate: candidate.confidence, reverse=True)

    def _choose_candidate(self, plan: ActionPlan, candidates: list[ResolvedTarget]) -> ResolvedTarget | None:
        if not candidates:
            return None
        best = candidates[0]
        minimum = 0.8
        if plan.action is ActionType.SEARCH:
            minimum = 0.9
        if best.confidence < minimum:
            return None
        if len(candidates) > 1 and best.confidence - candidates[1].confidence < 0.15:
            return None
        return best

    def _maybe_website(self, plan: ActionPlan) -> ResolvedTarget | None:
        lowered = plan.target_text.lower().strip()
        if lowered.startswith(("http://", "https://", "www.")):
            return self.website_resolver.resolve(plan)
        if " " not in lowered and len(lowered) > 1:
            return self.website_resolver.resolve(plan)
        return None

    def _execute_resolved(self, plan: ActionPlan, target: ResolvedTarget) -> tuple[bool, str | None]:
        if target.target_type is TargetType.WEBSITE:
            opened = self.browser.open_url(str(target.value))
            if not opened:
                return False, "Browser did not accept URL."
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
            process_hint = target.metadata.get("process_hint")
            previous_pids = self.app_executor.process_ids(str(process_hint)) if process_hint else set()
            launched = self.app_executor.open(target)
            running = self.app_executor.wait_for_running(str(process_hint), previous_pids) if process_hint else None
            if running is False:
                return False, "Launch command ran, but process was not detected."
            return launched, "Launch command issued; process verification unavailable." if running is None else "Process detected." if running else "Process not detected."
        return False, "Unsupported target type."

    def _message(self, plan: ActionPlan, target: ResolvedTarget, success: bool) -> str:
        if not success:
            return f"I could not verify that {plan.target_text} opened."
        if plan.action is ActionType.SEARCH:
            return f"Searched {target.name} for '{plan.query}'."
        if target.target_type is TargetType.WEBSITE:
            return f"Opened {target.name}."
        if plan.action is ActionType.CLOSE:
            return f"Closed {target.name}."
        if plan.action is ActionType.STATUS:
            return f"Checked {target.name}."
        return f"Opened {target.name}."

    def _clarification_message(self, plan: ActionPlan, candidates: list[ResolvedTarget]) -> str:
        if not candidates:
            return f"I could not find a safe target for '{plan.target_text}'."
        choices = "; ".join(f"{candidate.name} ({candidate.target_type.value}, {candidate.confidence:.2f})" for candidate in candidates[:3])
        return f"I am not confident enough to open '{plan.target_text}'. Did you mean: {choices}?"

    def _candidate_log(self, candidate: ResolvedTarget) -> dict[str, object]:
        return {
            "name": candidate.name,
            "type": candidate.target_type.value,
            "strategy": candidate.strategy.value,
            "confidence": candidate.confidence,
            "value": str(candidate.value),
        }

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
        candidates: list[ResolvedTarget] | None = None,
    ) -> ExecutionReport:
        return ExecutionReport(
            success=success,
            message=message,
            plan=plan,
            target=target,
            duration_ms=(time.perf_counter() - start) * 1000,
            verification=verification,
            error=error,
            candidates=candidates or [],
        )
