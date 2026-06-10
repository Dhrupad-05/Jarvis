from __future__ import annotations

import ctypes
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SystemManager:
    def mute(self) -> None:
        subprocess.run(["powershell", "-NoProfile", "-Command", "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"], check=False)

    def volume_key(self, direction: str, steps: int = 2) -> None:
        key = "[char]175" if direction == "up" else "[char]174"
        for _ in range(steps):
            subprocess.run(["powershell", "-NoProfile", "-Command", f"(New-Object -ComObject WScript.Shell).SendKeys({key})"], check=False)

    def set_brightness(self, percent: int) -> None:
        value = max(0, min(100, percent))
        command = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{value})"
        subprocess.run(["powershell", "-NoProfile", "-Command", command], check=False)

    def lock(self) -> None:
        ctypes.windll.user32.LockWorkStation()

    def sleep(self) -> None:
        subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=False)

    def shutdown(self) -> None:
        subprocess.run(["shutdown", "/s", "/t", "60"], check=False)

    def restart(self) -> None:
        subprocess.run(["shutdown", "/r", "/t", "60"], check=False)
