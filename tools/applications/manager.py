from __future__ import annotations

import subprocess
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ApplicationSpec:
    name: str
    aliases: tuple[str, ...]
    command: tuple[str, ...]
    process_names: tuple[str, ...]


@dataclass(slots=True)
class ApplicationManager:
    applications: dict[str, ApplicationSpec] = field(default_factory=dict)

    @classmethod
    def windows_defaults(cls) -> "ApplicationManager":
        specs = [
            ApplicationSpec("chrome", ("chrome", "google chrome"), ("cmd", "/c", "start", "", "chrome"), ("chrome",)),
            ApplicationSpec("vscode", ("vs code", "vscode", "code"), ("cmd", "/c", "start", "", "code"), ("Code",)),
            ApplicationSpec("notepad", ("notepad",), ("notepad",), ("notepad",)),
            ApplicationSpec("calculator", ("calculator", "calc"), ("calc",), ("CalculatorApp", "Calculator")),
            ApplicationSpec("spotify", ("spotify",), ("cmd", "/c", "start", "", "spotify:"), ("Spotify",)),
        ]
        return cls({spec.name: spec for spec in specs})

    def resolve(self, text: str) -> ApplicationSpec | None:
        lowered = text.lower()
        for spec in self.applications.values():
            if any(alias in lowered for alias in spec.aliases):
                return spec
        return None

    def open(self, spec: ApplicationSpec) -> None:
        subprocess.Popen(spec.command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def close(self, spec: ApplicationSpec) -> bool:
        closed = False
        for process in spec.process_names:
            result = subprocess.run(
                ["taskkill", "/IM", f"{process}.exe", "/F"],
                capture_output=True,
                text=True,
                check=False,
            )
            closed = closed or result.returncode == 0
        return closed

    def is_running(self, spec: ApplicationSpec) -> bool:
        result = subprocess.run(["tasklist"], capture_output=True, text=True, check=False)
        output = result.stdout.lower()
        return any(f"{name.lower()}.exe" in output for name in spec.process_names)
