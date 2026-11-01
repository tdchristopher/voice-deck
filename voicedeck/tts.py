"""Text-to-speech with Piper (MIT). The voice model stays loaded for fast replies."""
import tempfile
import threading
import wave

from .config import resolve_path


class TTS:
    def __init__(self, cfg, audio=None, quiet=False):
        self.audio = audio
        self.quiet = quiet or audio is None
        self.lock = threading.Lock()  # reminders and the main loop can both speak
        self.voice = None
        if self.quiet:
            return
        path = resolve_path(cfg, (cfg.get("tts", {}) or {}).get("voice", "voices/en_US-lessac-medium.onnx"))
        if not path.exists():
            print(f"[tts] voice not found at {path}; replies will be printed only. Run install.sh.")
            return
        from piper import PiperVoice
        self.voice = PiperVoice.load(str(path))

    def say(self, text):
        print(f"🔊 {text}")
        if self.quiet or self.voice is None:
            return
        with self.lock, tempfile.NamedTemporaryFile(suffix=".wav") as f:
            with wave.open(f.name, "wb") as w:
                if hasattr(self.voice, "synthesize_wav"):   # piper-tts >= 1.3
                    self.voice.synthesize_wav(text, w)
                else:                                       # piper-tts 1.2
                    self.voice.synthesize(text, w)
            self.audio.play_wav(f.name)
