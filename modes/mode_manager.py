from __future__ import annotations

from dataclasses import dataclass, field

from core.config import Settings
from modes.modes import AssistantMode, default_modes


@dataclass(slots=True)
class ModeManager:
    modes: dict[str, AssistantMode]
    active_mode_key: str = "productivity"

    @classmethod
    def from_settings(cls, settings: Settings) -> "ModeManager":
        manager = cls(modes=default_modes())
        manager.set_mode(settings.default_mode)
        return manager

    @property
    def active_mode(self) -> AssistantMode:
        return self.modes[self.active_mode_key]

    def set_mode(self, mode_name: str) -> AssistantMode:
        key = mode_name.strip().lower()
        if key not in self.modes:
            available = ", ".join(self.available_mode_names())
            raise ValueError(f"Unknown mode '{mode_name}'. Available modes: {available}")
        self.active_mode_key = key
        return self.active_mode

    def available_mode_names(self) -> list[str]:
        return sorted(self.modes.keys())

