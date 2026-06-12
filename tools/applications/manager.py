from __future__ import annotations

import subprocess
import time
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
        return any(self.process_ids(name) for name in spec.process_names)

    def process_ids(self, process_name: str) -> set[int]:
        image = process_name if process_name.lower().endswith(".exe") else f"{process_name}.exe"
        result = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {image}", "/FO", "CSV", "/NH"], capture_output=True, text=True, check=False)
        pids: set[int] = set()
        for line in result.stdout.splitlines():
            parts = [part.strip().strip('"') for part in line.split(",")]
            if len(parts) >= 2 and parts[0].lower() == image.lower():
                try:
                    pids.add(int(parts[1]))
                except ValueError:
                    continue
        return pids

    def wait_until_running(self, spec: ApplicationSpec, timeout_seconds: float = 4.0) -> bool:
        deadline = time.perf_counter() + timeout_seconds
        while time.perf_counter() < deadline:
            if self.is_running(spec):
                return True
            time.sleep(0.25)
        return False
