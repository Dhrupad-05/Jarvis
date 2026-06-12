from __future__ import annotations

import importlib.util
import shutil
from dataclasses import dataclass

from core.config import Settings


@dataclass(frozen=True, slots=True)
class VoiceDiagnostics:
    sounddevice_available: bool
    faster_whisper_available: bool
    piper_available: bool
    piper_voice_configured: bool
    tts_enabled: bool
    voice_enabled: bool

    @property
    def usable_for_listening(self) -> bool:
        return self.voice_enabled and self.sounddevice_available and self.faster_whisper_available

    @property
    def usable_for_speaking(self) -> bool:
        return not self.tts_enabled or (self.piper_available and self.piper_voice_configured)

    def messages(self) -> list[str]:
        messages: list[str] = []
        if not self.voice_enabled:
            messages.append("Voice mode is disabled. Set ENABLE_VOICE=true.")
        if not self.sounddevice_available:
            messages.append("Missing dependency: sounddevice.")
        if not self.faster_whisper_available:
            messages.append("Missing dependency: faster-whisper.")
        if self.tts_enabled and not self.piper_available:
            messages.append("Piper executable was not found.")
        if self.tts_enabled and not self.piper_voice_configured:
            messages.append("PIPER_VOICE is not configured.")
        return messages


def run_voice_diagnostics(settings: Settings) -> VoiceDiagnostics:
    return VoiceDiagnostics(
        sounddevice_available=importlib.util.find_spec("sounddevice") is not None,
        faster_whisper_available=importlib.util.find_spec("faster_whisper") is not None,
        piper_available=shutil.which(settings.piper_executable) is not None,
        piper_voice_configured=bool(settings.piper_voice),
        tts_enabled=settings.tts_enabled,
        voice_enabled=settings.voice_enabled,
    )
