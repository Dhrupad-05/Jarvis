from __future__ import annotations

import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

from core.exceptions import VoiceError


@dataclass(slots=True)
class MicrophoneRecorder:
    sample_rate: int = 16_000
    channels: int = 1

    def record_push_to_talk(self, seconds: float = 5.0) -> Path:
        try:
            import sounddevice as sd
        except ImportError as exc:
            raise VoiceError("Microphone recording requires the 'sounddevice' package.") from exc

        frames = int(seconds * self.sample_rate)
        audio = sd.rec(frames, samplerate=self.sample_rate, channels=self.channels, dtype="int16")
        sd.wait()

        output = Path(tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name)
        with wave.open(str(output), "wb") as wav:
            wav.setnchannels(self.channels)
            wav.setsampwidth(2)
            wav.setframerate(self.sample_rate)
            wav.writeframes(audio.tobytes())
        return output
