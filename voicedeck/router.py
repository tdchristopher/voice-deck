"""Decide what the user wants.

Fast path: regular expressions handle common phrasings instantly.
Slow path: anything else goes to the local LLM, which returns structured JSON.
"""
import re
from dataclasses import dataclass, field

INTENTS = ["slack_post", "slack_catchup", "calendar_day", "calendar_add",
           "reminder", "chat", "cancel", "unknown"]


@dataclass
class Intent:
    name: str
    slots: dict = field(default_factory=dict)
    source: str = "regex"


_CHANNEL = r"#?(?P<channel>[a-z0-9][\w-]*)"
_WHEN_START = r"(?:in|at|on|tomorrow|today|tonight|next|this|noon|monday|tuesday|wednesday|thursday|friday|saturday|sunday)"

PATTERNS = [
    ("cancel", re.compile(r"^(?:cancel|never ?mind|stop|forget it)\W*$", re.I)),
    ("slack_post", re.compile(
        r"^(?:post|send|message|slack)(?: a message)?(?: to| in)? (?:the )?" + _CHANNEL +
        r"(?: channel)?\s*[,:\-]?\s*(?:saying|that says|that)?\s*[,:]?\s*(?P<message>.+)$", re.I)),
    ("slack_catchup", re.compile(
        r"^(?:what did i miss|catch me up|any(?: new)? messages)(?: (?:in|on) (?:the )?" + _CHANNEL +
        r"(?: channel)?)?\W*$", re.I)),
    ("calendar_day", re.compile(
        r"^(?:what'?s|what is|read|check|tell me)(?: on)?(?: me)? (?:my )?(?:calendar|schedule|agenda)"
        r"(?: (?:for|on))?(?: (?P<day>today|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday))?\W*$",
        re.I)),
    ("calendar_day", re.compile(
        r"^what(?:'s| is| do i have)(?: going on| happening| on)? (?P<day>today|tomorrow)\W*$", re.I)),
    ("reminder", re.compile(
        r"^remind me (?P<when>" + _WHEN_START + r"\b.*?)(?:,)? (?:to |that |about )(?P<message>.+?)\W*$", re.I)),
    ("reminder", re.compile(
        r"^remind me (?:to |that |about )?(?P<message>.+?),? (?P<when>" + _WHEN_START + r"\b.*?)\W*$", re.I)),
]

SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": INTENTS},
        "channel": {"type": "string"},
        "message": {"type": "string"},
        "title": {"type": "string"},
        "when": {"type": "string"},
        "day": {"type": "string"},
    },
    "required": ["intent"],
}

SYSTEM = """You turn a spoken command into JSON. Pick one intent:
- slack_post: post a message to Slack. Fill channel (no #) and message (the exact words to post).
- slack_catchup: summarize recent Slack messages. Fill channel if one is named.
- calendar_day: read the calendar. Fill day (e.g. "today", "tomorrow", "friday").
- calendar_add: create a calendar event. Fill title and when (copy the time words exactly, e.g. "friday at 3 pm").
- reminder: a reminder. Fill message and when (copy the time words exactly, e.g. "in 20 minutes").
- chat: a general question or conversation that needs a spoken answer.
- cancel: the user wants to stop or cancel.
- unknown: unclear or empty.
Only output JSON.

Examples:
"tell the design channel the mockups are ready" -> {"intent":"slack_post","channel":"design","message":"The mockups are ready"}
"put dentist on my calendar thursday at 10" -> {"intent":"calendar_add","title":"Dentist","when":"thursday at 10 am"}
"schedule a call with Maya tomorrow at 2 pm" -> {"intent":"calendar_add","title":"Call with Maya","when":"tomorrow at 2 pm"}
"in an hour remind me to feed the cats" -> {"intent":"reminder","message":"feed the cats","when":"in 1 hour"}
"do I have anything friday" -> {"intent":"calendar_day","day":"friday"}
"how far is the moon" -> {"intent":"chat"}"""


def _clean(slots):
    out = {}
    for k, v in slots.items():
        if isinstance(v, str):
            v = v.strip().strip(",").strip()
            if k == "channel":
                v = v.lstrip("#").lower().replace(" ", "-")
            if v:
                out[k] = v
    return out


def route_regex(text):
    t = text.strip()
    for name, pat in PATTERNS:
        m = pat.match(t)
        if m:
            return Intent(name, _clean({k: v for k, v in m.groupdict().items() if v}))
    return None


def route(text, llm=None):
    if not text or not text.strip():
        return Intent("unknown")
    hit = route_regex(text)
    if hit:
        return hit
    if llm is None:
        return Intent("unknown")
    data = llm.chat_json(SYSTEM, text.strip(), SCHEMA)
    name = data.pop("intent", "unknown")
    if name not in INTENTS:
        name = "unknown"
    return Intent(name, _clean(data), source="llm")
