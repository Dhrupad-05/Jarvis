from __future__ import annotations

import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

from core.audit import log_action
from core.config import Settings
from core.exceptions import VoiceError


@dataclass(slots=True)
class PiperSpeaker:
    settings: Settings

    def speak(self, text: str) -> None:
        if not self.settings.tts_enabled:
            return
        if not self.settings.piper_voice:
            raise VoiceError("Piper voice is not configured. Set PIPER_VOICE in .env.")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            wav_path = Path(tmp.name)
        command = [
            self.settings.piper_executable,
            "--model",
            self.settings.piper_voice,
            "--output_file",
            str(wav_path),
        ]
        try:
            result = subprocess.run(command, input=text, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                raise VoiceError(result.stderr.strip() or "Piper failed to synthesize speech.")
            self._play_wav(wav_path)
            log_action("tts_playback", "success", chars=len(text), file=str(wav_path))
        finally:
            try:
                wav_path.unlink(missing_ok=True)
                log_action("tts_temp_cleanup", "success", file=str(wav_path))
            except Exception as exc:
                log_action("tts_temp_cleanup", "failed", file=str(wav_path), error=str(exc))

    def _play_wav(self, wav_path: Path) -> None:
        try:
            import sounddevice as sd
            import numpy as np
        except ImportError:
            subprocess.run(["powershell", "-NoProfile", "-Command", f"(New-Object Media.SoundPlayer '{wav_path}').PlaySync();"], check=False)
            return
        with wave.open(str(wav_path), "rb") as wav:
            frames = wav.readframes(wav.getnframes())
            audio = np.frombuffer(frames, dtype="int16")
            if wav.getnchannels() > 1:
                audio = audio.reshape(-1, wav.getnchannels())
            sd.play(audio, wav.getframerate())
            sd.wait()
