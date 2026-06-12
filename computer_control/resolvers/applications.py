from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path

from computer_control.models import ResolutionStrategy, ResolvedTarget, TargetType, VerificationResult
from computer_control.text import normalize_target, title_name


@dataclass(frozen=True, slots=True)
class ApplicationCandidate:
    name: str
    command: tuple[str, ...] | str | Path
    strategy: ResolutionStrategy
    process_hint: str | None = None
    confidence: float = 0.7


@dataclass(slots=True)
class ApplicationResolver:
    known_commands: dict[str, ApplicationCandidate] = field(default_factory=dict)

    @classmethod
    def defaults(cls) -> "ApplicationResolver":
        known = {
            "chrome": ApplicationCandidate("Chrome", ("cmd", "/c", "start", "", "chrome"), ResolutionStrategy.KNOWN_REGISTRY, "chrome", 0.96),
            "edge": ApplicationCandidate("Microsoft Edge", ("cmd", "/c", "start", "", "msedge"), ResolutionStrategy.KNOWN_REGISTRY, "msedge", 0.94),
            "vscode": ApplicationCandidate("VS Code", ("cmd", "/c", "start", "", "code"), ResolutionStrategy.KNOWN_REGISTRY, "Code", 0.95),
            "code": ApplicationCandidate("VS Code", ("cmd", "/c", "start", "", "code"), ResolutionStrategy.KNOWN_REGISTRY, "Code", 0.95),
            "notepad": ApplicationCandidate("Notepad", ("notepad",), ResolutionStrategy.KNOWN_REGISTRY, "notepad", 0.96),
            "calculator": ApplicationCandidate("Calculator", ("calc",), ResolutionStrategy.KNOWN_REGISTRY, "Calculator", 0.95),
            "calc": ApplicationCandidate("Calculator", ("calc",), ResolutionStrategy.KNOWN_REGISTRY, "Calculator", 0.95),
            "camera": ApplicationCandidate("Camera", ("cmd", "/c", "start", "", "microsoft.windows.camera:"), ResolutionStrategy.KNOWN_REGISTRY, "WindowsCamera", 0.88),
            "powershell": ApplicationCandidate("PowerShell", ("cmd", "/c", "start", "", "powershell", "-NoExit"), ResolutionStrategy.KNOWN_REGISTRY, "powershell", 0.95),
            "commandprompt": ApplicationCandidate("Command Prompt", ("cmd", "/c", "start", "", "cmd", "/K"), ResolutionStrategy.KNOWN_REGISTRY, "cmd", 0.95),
            "cmd": ApplicationCandidate("Command Prompt", ("cmd", "/c", "start", "", "cmd", "/K"), ResolutionStrategy.KNOWN_REGISTRY, "cmd", 0.95),
            "taskmanager": ApplicationCandidate("Task Manager", ("taskmgr",), ResolutionStrategy.KNOWN_REGISTRY, "Taskmgr", 0.95),
            "devicemanager": ApplicationCandidate("Device Manager", ("devmgmt.msc",), ResolutionStrategy.KNOWN_REGISTRY, "mmc", 0.95),
            "settings": ApplicationCandidate("Settings", ("cmd", "/c", "start", "", "ms-settings:"), ResolutionStrategy.KNOWN_REGISTRY, "SystemSettings", 0.95),
            "controlpanel": ApplicationCandidate("Control Panel", ("control",), ResolutionStrategy.KNOWN_REGISTRY, "control", 0.95),
            "fileexplorer": ApplicationCandidate("File Explorer", ("explorer",), ResolutionStrategy.KNOWN_REGISTRY, "explorer", 0.95),
            "explorer": ApplicationCandidate("File Explorer", ("explorer",), ResolutionStrategy.KNOWN_REGISTRY, "explorer", 0.95),
        }
        return cls(known)

    def resolve(self, target_text: str) -> ResolvedTarget:
        query = target_text.strip()
        key = normalize_target(query)
        candidate = (
            self._known(key)
            or self._start_menu(query)
            or self._installed_application(query)
            or self._path_executable(query)
            or self._shell_candidate(query)
            or self._windows_search(query)
        )
        return ResolvedTarget(
            name=candidate.name,
            target_type=TargetType.APPLICATION,
            value=candidate.command,
            strategy=candidate.strategy,
            confidence=candidate.confidence,
            metadata={"process_hint": candidate.process_hint},
        )

    def _known(self, key: str) -> ApplicationCandidate | None:
        return self.known_commands.get(key)

    def _start_menu(self, query: str) -> ApplicationCandidate | None:
        query_key = normalize_target(query)
        roots = [
            Path(os.environ.get("ProgramData", r"C:\ProgramData")) / r"Microsoft\Windows\Start Menu\Programs",
            Path(os.environ.get("AppData", "")) / r"Microsoft\Windows\Start Menu\Programs",
        ]
        best: Path | None = None
        for root in roots:
            if not root.exists():
                continue
            for suffix in ("*.lnk", "*.url"):
                for path in root.rglob(suffix):
                    if query_key in normalize_target(path.stem):
                        best = path
                        break
                if best:
                    break
            if best:
                break
        if best is None:
            return None
        return ApplicationCandidate(best.stem, best, ResolutionStrategy.START_MENU, best.stem, 0.9)

    def _installed_application(self, query: str) -> ApplicationCandidate | None:
        try:
            import winreg
        except ImportError:
            return None
        query_key = normalize_target(query)
        roots = [
            (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        ]
        for hive, path in roots:
            try:
                with winreg.OpenKey(hive, path) as root:
                    for index in range(winreg.QueryInfoKey(root)[0]):
                        try:
                            subkey_name = winreg.EnumKey(root, index)
                            with winreg.OpenKey(root, subkey_name) as subkey:
                                name = str(winreg.QueryValueEx(subkey, "DisplayName")[0])
                                if query_key not in normalize_target(name):
                                    continue
                                command = self._registry_launch_command(subkey)
                                if command:
                                    return ApplicationCandidate(name, command, ResolutionStrategy.INSTALLED_APPLICATION, name, 0.82)
                        except OSError:
                            continue
            except OSError:
                continue
        return None

    def _registry_launch_command(self, subkey: object) -> tuple[str, ...] | None:
        try:
            import winreg
            icon = str(winreg.QueryValueEx(subkey, "DisplayIcon")[0]).strip('"')
            exe = icon.split(",", 1)[0]
            if exe.lower().endswith(".exe") and Path(exe).exists():
                return (exe,)
        except OSError:
            return None
        return None

    def _path_executable(self, query: str) -> ApplicationCandidate | None:
        names = [query, query.replace(" ", ""), query.replace(" ", "-"), query.replace(" ", "_")]
        for name in names:
            executable = shutil.which(name) or shutil.which(f"{name}.exe")
            if executable:
                return ApplicationCandidate(title_name(query), (executable,), ResolutionStrategy.PATH_EXECUTABLE, Path(executable).stem, 0.86)
        return None

    def _shell_candidate(self, query: str) -> ApplicationCandidate:
        return ApplicationCandidate(title_name(query), ("cmd", "/c", "start", "", query), ResolutionStrategy.SHELL_EXECUTION, query.split()[0], 0.55)

    def _windows_search(self, query: str) -> ApplicationCandidate:
        return ApplicationCandidate(
            title_name(query),
            ("explorer.exe", f"search-ms:query={query}"),
            ResolutionStrategy.WINDOWS_SEARCH,
            None,
            0.35,
        )


@dataclass(frozen=True, slots=True)
class ApplicationExecutor:
    def process_ids(self, process_hint: str | None) -> set[int]:
        if not process_hint:
            return set()
        process_name = process_hint if process_hint.lower().endswith(".exe") else f"{process_hint}.exe"
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {process_name}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        )
        pids: set[int] = set()
        for line in result.stdout.splitlines():
            if not line.strip() or "No tasks are running" in line:
                continue
            parts = [part.strip().strip('"') for part in line.split(",")]
            if len(parts) >= 2 and parts[0].lower() == process_name.lower():
                try:
                    pids.add(int(parts[1]))
                except ValueError:
                    continue
        return pids

    def open(self, target: ResolvedTarget) -> bool:
        command = target.value
        if isinstance(command, Path):
            os.startfile(command)  # type: ignore[attr-defined]
            return True
        if isinstance(command, str):
            subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        subprocess.Popen(list(command), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True

    def close(self, target_name: str) -> bool:
        process = target_name if target_name.lower().endswith(".exe") else f"{target_name}.exe"
        result = subprocess.run(["taskkill", "/IM", process, "/F"], capture_output=True, text=True, check=False)
        return result.returncode == 0

    def is_running(self, process_hint: str | None) -> bool | None:
        if not process_hint:
            return None
        return bool(self.process_ids(process_hint))

    def wait_for_running(self, process_hint: str | None, previous_pids: set[int], timeout_seconds: float = 4.0) -> bool | None:
        if not process_hint:
            return None
        deadline = time.perf_counter() + timeout_seconds
        while time.perf_counter() < deadline:
            current = self.process_ids(process_hint)
            if current:
                if current - previous_pids or current == previous_pids:
                    return True
            time.sleep(0.25)
        return False

    def verify_launch(self, process_hint: str | None, previous_pids: set[int], timeout_seconds: float = 4.0) -> VerificationResult:
        if not process_hint:
            return VerificationResult(True, "Launch command accepted; no process hint available.", "unavailable", None)
        running = self.wait_for_running(process_hint, previous_pids, timeout_seconds=timeout_seconds)
        if running is True:
            current = self.process_ids(process_hint)
            if current - previous_pids:
                return VerificationResult(True, "New process detected.", "tasklist", True)
            return VerificationResult(True, "Process is running; application may have reused an existing instance.", "tasklist", True)
        if running is None:
            return VerificationResult(True, "Launch command accepted; verification unavailable.", "unavailable", None)
        return VerificationResult(False, "Launch command ran, but process was not detected.", "tasklist", False)
