from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from computer_control.models import ActionPlan, ResolutionStrategy, ResolvedTarget, TargetType


SPECIAL_FOLDERS = {
    "downloads": Path.home() / "Downloads",
    "desktop": Path.home() / "Desktop",
    "documents": Path.home() / "Documents",
    "home": Path.home(),
}


@dataclass(frozen=True, slots=True)
class FilesystemResolver:
    project_root: Path

    def resolve(self, plan: ActionPlan) -> ResolvedTarget | None:
        target = plan.target_text.lower().replace("my ", "").replace("the ", "").strip()
        for name, path in SPECIAL_FOLDERS.items():
            if name in target:
                return ResolvedTarget(name, TargetType.FOLDER, path, ResolutionStrategy.SPECIAL_FOLDER, 0.9)
        if "project" in target or "ai assistant" in target:
            return ResolvedTarget("project folder", TargetType.FOLDER, self.project_root, ResolutionStrategy.SPECIAL_FOLDER, 0.9)
        return None


@dataclass(frozen=True, slots=True)
class FilesystemExecutor:
    def open(self, target: ResolvedTarget) -> bool:
        path = Path(target.value)
        if not path.exists():
            return False
        os.startfile(path)  # type: ignore[attr-defined]
        return True
