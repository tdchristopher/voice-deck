"""Microphone capture with simple silence detection, plus playback and earcons."""
import collections
import time
import wave

import numpy as np


def _sd():
    import sounddevice as sd  # imported lazily so --text mode works without audio libs
    return sd


def rms(x):
    x = np.asarray(x, dtype=np.float32)
    return float(np.sqrt(np.mean(x * x))) if x.size else 0.0


class Audio:
    def __init__(self, cfg):
        a = cfg.get("audio", {}) or {}
        self.rate = a.get("sample_rate", 16000)
        self.in_dev = a.get("input_device")
        self.out_dev = a.get("output_device")
        self.silence_seconds = a.get("silence_seconds", 0.8)
        self.max_seconds = a.get("max_seconds", 12)
        self.threshold = a.get("energy_threshold")
        self.block = int(self.rate * 0.03)  # 30 ms frames

    # ---------- input ----------
    def calibrate(self, seconds=1.0):
        sd = _sd()
        rec = sd.rec(int(seconds * self.rate), samplerate=self.rate, channels=1,
                     dtype="int16", device=self.in_dev)
        sd.wait()
        self.threshold = max(rms(rec) * 3.0, 300.0)
        print(f"[audio] noise threshold set to {self.threshold:.0f}")
        return self.threshold

    def record_utterance(self, wait_for_speech=5.0):
        """Record until the speaker stops. Returns float32 mono audio at 16 kHz, or None."""
        sd = _sd()
        if self.threshold is None:
            self.calibrate()
        preroll = collections.deque(maxlen=10)  # keep ~300 ms before speech starts
        frames, started, silent = [], False, 0.0
        t0 = time.time()
        with sd.InputStream(samplerate=self.rate, channels=1, dtype="int16",
                            blocksize=self.block, device=self.in_dev) as stream:
            while True:
                data, _ = stream.read(self.block)
                loud = rms(data) > self.threshold
                if not started:
                    preroll.append(data.copy())
                    if loud:
                        started = True
                        frames.extend(preroll)
                    elif time.time() - t0 > wait_for_speech:
                        return None
                    continue
                frames.append(data.copy())
                silent = 0.0 if loud else silent + self.block / self.rate
                duration = len(frames) * self.block / self.rate
                if silent >= self.silence_seconds or duration >= self.max_seconds:
                    break
        audio = np.concatenate(frames).flatten().astype(np.float32) / 32768.0
        return audio

    # ---------- output ----------
    def play(self, samples, rate):
        sd = _sd()
        sd.play(samples, samplerate=rate, device=self.out_dev)
        sd.wait()

    def play_wav(self, path):
        with wave.open(str(path), "rb") as w:
            rate = w.getframerate()
            data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
            if w.getnchannels() > 1:
                data = data.reshape(-1, w.getnchannels())
        self.play(data, rate)

    def earcon(self, kind):
        """Short tones: 'listen' (rising), 'done' (falling), 'error' (low)."""
        notes = {"listen": [660, 880], "done": [880, 660], "error": [300, 220]}.get(kind, [440])
        rate = 22050
        parts = []
        for f in notes:
            t = np.linspace(0, 0.08, int(rate * 0.08), endpoint=False)
            env = np.minimum(1, np.minimum(t, 0.08 - t) * 60)  # soft attack/release
            parts.append(0.25 * np.sin(2 * np.pi * f * t) * env)
        try:
            self.play(np.concatenate(parts).astype(np.float32), rate)
        except Exception as e:  # never let a beep crash the assistant
            print(f"[audio] earcon failed: {e}")
