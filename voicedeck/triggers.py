"""Ways to start listening: Enter key, wake word, or a GPIO button."""


class KeyboardTrigger:
    def wait(self):
        input("\n⏎  Press Enter and speak... ")


class GpioTrigger:
    def __init__(self, cfg):
        from gpiozero import Button  # preinstalled on Raspberry Pi OS
        pin = (cfg.get("gpio", {}) or {}).get("button_pin", 17)
        self.button = Button(pin)
        print(f"[trigger] push-to-talk button on GPIO{pin}")

    def wait(self):
        self.button.wait_for_press()


class WakeWordTrigger:
    def __init__(self, cfg, audio):
        try:
            import openwakeword
            from openwakeword.model import Model
        except ImportError as e:
            raise SystemExit(
                "openWakeWord isn't installed. Run: ./install.sh --wakeword  "
                "(or set trigger: keyboard / gpio in config.yaml)") from e
        w = cfg.get("wakeword", {}) or {}
        self.name = w.get("model", "hey_jarvis")
        self.threshold = w.get("threshold", 0.5)
        self.audio = audio
        try:
            openwakeword.utils.download_models([self.name])
        except Exception as e:
            print(f"[wakeword] model download skipped: {e}")
        self.model = Model(wakeword_models=[self.name], inference_framework="onnx")
        print(f"[trigger] listening for wake word '{self.name}'")

    def wait(self):
        import sounddevice as sd
        self.model.reset()
        with sd.InputStream(samplerate=16000, channels=1, dtype="int16",
                            blocksize=1280, device=self.audio.in_dev) as stream:
            while True:
                data, _ = stream.read(1280)
                scores = self.model.predict(data.flatten())
                if scores and max(scores.values()) >= self.threshold:
                    return


def make_trigger(cfg, audio):
    kind = cfg.get("trigger", "keyboard")
    if kind == "wakeword":
        return WakeWordTrigger(cfg, audio)
    if kind == "gpio":
        return GpioTrigger(cfg)
    return KeyboardTrigger()
