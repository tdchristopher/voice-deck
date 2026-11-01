"""The main loop: trigger -> listen -> transcribe -> route -> act -> speak."""
import re
import traceback
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from .llm import LLM
from .router import route
from .timeparse import parse_when, spoken

YES = re.compile(r"\b(yes|yeah|yep|yup|sure|confirm|do it|send it|go ahead|correct|ok(ay)?)\b", re.I)
NO = re.compile(r"\b(no|nope|cancel|stop|don'?t|wait)\b", re.I)


class Assistant:
    def __init__(self, cfg, text_mode=False, quiet=False):
        self.cfg = cfg
        self.text_mode = text_mode
        self.tz = (cfg.get("calendar", {}) or {}).get("timezone", "America/Los_Angeles")
        self.llm = LLM(cfg)

        self.audio = None
        if not (text_mode and quiet):
            from .audio import Audio
            self.audio = Audio(cfg)

        from .tts import TTS
        self.tts = TTS(cfg, self.audio, quiet=quiet)

        self.stt = None
        if not text_mode:
            from .stt import STT
            self.stt = STT(cfg)

        self.slack = self._optional("slack", "actions.slack", "Slack")
        self.calendar = self._optional("calendar", "actions.gcal", "Calendar")

        from .actions.reminders import Reminders
        self.reminders = Reminders(cfg, lambda msg: self._remind(msg))

    def _optional(self, key, module, cls):
        if not (self.cfg.get(key, {}) or {}).get("enabled", True):
            return None
        try:
            mod = __import__(f"voicedeck.{module}", fromlist=[cls])
            return getattr(mod, cls)(self.cfg)
        except Exception as e:
            print(f"[{key}] disabled: {e}")
            return None

    # ---------- I/O helpers ----------
    def say(self, text):
        self.tts.say(text)

    def beep(self, kind):
        if self.audio and not self.text_mode:
            self.audio.earcon(kind)

    def listen(self):
        if self.text_mode:
            try:
                return input("you> ").strip()
            except EOFError:
                raise KeyboardInterrupt
        self.beep("listen")
        audio = self.audio.record_utterance()
        self.beep("done")
        if audio is None:
            return ""
        text = self.stt.transcribe(audio)
        print(f"🎤 {text}")
        return text

    def confirm(self, question):
        self.say(question)
        answer = self.listen()
        return bool(YES.search(answer)) and not NO.search(answer)

    def _remind(self, message):
        self.beep("listen")
        self.say(f"Reminder: {message}")

    # ---------- intent handlers ----------
    def handle(self, text):
        if not text:
            self.say("I didn't hear anything.")
            return
        try:
            intent = route(text, self.llm)
        except Exception as e:
            print(f"[router] {e}")
            self.say("I couldn't reach the language model. Is Ollama running?")
            return
        print(f"[intent] {intent.name} {intent.slots} ({intent.source})")
        handler = getattr(self, f"do_{intent.name}", self.do_unknown)
        try:
            handler(_text=text, **intent.slots)
        except Exception as e:
            traceback.print_exc()
            self.beep("error")
            self.say(f"Something went wrong. {str(e)[:120]}")

    def do_cancel(self, **_):
        self.say("Okay.")

    def do_unknown(self, **_):
        self.say("Sorry, I didn't catch that.")

    def do_chat(self, _text="", **_):
        reply = self.llm.chat(
            "You are a voice assistant on a Raspberry Pi. Answer in one or two short spoken "
            "sentences. No lists or markdown.", _text)
        self.say(reply)

    def do_slack_post(self, channel=None, message=None, **_):
        if not self.slack:
            return self.say("Slack isn't set up yet.")
        if not message:
            return self.say("What should I post?")
        channel = channel or self.slack.default
        if self.confirm(f"Post to {channel}: {message}. Send it?"):
            self.slack.post(channel, message)
            self.say("Posted.")
        else:
            self.say("Okay, not sent.")

    def do_slack_catchup(self, channel=None, **_):
        if not self.slack:
            return self.say("Slack isn't set up yet.")
        channel = channel or self.slack.default
        lines = self.slack.recent(channel)
        if not lines:
            return self.say(f"Nothing new in {channel}.")
        summary = self.llm.chat(
            "Summarize these Slack messages for someone listening, in 2 or 3 short spoken "
            "sentences. Mention who said what if it matters. No lists, no markdown.",
            "\n".join(lines))
        self.say(summary)

    def do_calendar_day(self, day="today", **_):
        if not self.calendar:
            return self.say("Your calendar isn't connected yet.")
        when = parse_when(day or "today", self.tz)
        if when is None:
            return self.say(f"I'm not sure which day {day} is.")
        events = self.calendar.events_on(when.date())
        label = spoken(when).split(" at ")[0]
        if not events:
            return self.say(f"Nothing on your calendar {label}.")
        parts = [f"{title} at {t}" if t != "all day" else f"{title}, all day" for t, title in events]
        n = len(events)
        self.say(f"You have {n} event{'s' if n > 1 else ''} {label}: " + "; ".join(parts) + ".")

    def do_calendar_add(self, title=None, when=None, **_):
        if not self.calendar:
            return self.say("Your calendar isn't connected yet.")
        start = parse_when(when, self.tz)
        if not title or start is None:
            return self.say("I need a title and a time. Try: add dentist Friday at 3 PM.")
        if self.confirm(f"Add {title}, {spoken(start)}?"):
            self.calendar.add(title, start)
            self.say("Added to your calendar.")
        else:
            self.say("Okay, I didn't add it.")

    def do_reminder(self, message=None, when=None, **_):
        due = parse_when(when, self.tz)
        if not message or due is None:
            return self.say("Try: remind me in 20 minutes to check the oven.")
        if due <= datetime.now(ZoneInfo(self.tz)):
            due += timedelta(days=1)
        self.reminders.add(due, message)
        self.say(f"Okay, I'll remind you {spoken(due)}.")

    # ---------- main loop ----------
    def run(self):
        from .triggers import make_trigger
        name = self.cfg.get("assistant_name", "Deck")
        self.llm.warmup()
        trigger = None if self.text_mode else make_trigger(self.cfg, self.audio)
        if self.text_mode:
            print("Text mode: type a command (Ctrl+C to quit).")
        self.say(f"{name} is ready.")
        try:
            while True:
                if trigger:
                    trigger.wait()
                self.handle(self.listen())
        except KeyboardInterrupt:
            print("\nBye.")
