"""Speech-to-text with faster-whisper (MIT), running locally on the CPU."""


class STT:
    def __init__(self, cfg):
        from faster_whisper import WhisperModel
        s = cfg.get("stt", {}) or {}
        name = s.get("model", "base.en")
        print(f"[stt] loading whisper '{name}' (first run downloads it)...")
        self.model = WhisperModel(name, device="cpu", compute_type=s.get("compute_type", "int8"))

    def transcribe(self, audio):
        segments, _ = self.model.transcribe(audio, beam_size=1, language="en")
        return " ".join(seg.text.strip() for seg in segments).strip()
