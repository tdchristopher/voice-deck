"""Turn spoken times ("tomorrow at 3 p.m.", "in 10 minutes") into datetimes."""
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import dateparser

_SUBS = [
    (r"\b(\d{1,2})\s*([ap])\.?\s*m\.?", r"\1 \2m"),   # 3 p.m. -> 3 pm
    (r"\bnoon\b", "12:00 pm"),
    (r"\bmidnight\b", "12:00 am"),
    (r"\btonight\b", "today 8 pm"),
    (r"\bthis morning\b", "today 9 am"),
    (r"\bthis afternoon\b", "today 3 pm"),
    (r"\bthis evening\b", "today 6 pm"),
    (r"\bhalf an hour\b", "30 minutes"),
    (r"\ban hour\b", "1 hour"),
]

_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def normalize(when):
    s = when.lower().strip().rstrip(".?!")
    s = re.sub(r"^(on|at|for)\s+", "", s)
    for pat, rep in _SUBS:
        s = re.sub(pat, rep, s)
    # "next friday" -> "friday" (dateparser prefers the future anyway)
    s = re.sub(r"\bnext\s+(" + "|".join(_WEEKDAYS) + r")\b", r"\1", s)
    s = re.sub(r"\s+at\s+", " ", s)
    return s


def parse_when(when, tz="America/Los_Angeles", now=None):
    """Return a timezone-aware datetime, or None if it can't be understood."""
    if not when:
        return None
    zone = ZoneInfo(tz)
    now = now or datetime.now(zone)
    settings = {
        "PREFER_DATES_FROM": "future",
        "TIMEZONE": tz,
        "RETURN_AS_TIMEZONE_AWARE": True,
        "RELATIVE_BASE": now.replace(tzinfo=None),
    }
    dt = dateparser.parse(normalize(when), languages=["en"], settings=settings)
    if dt is None:
        return None
    dt = dt.astimezone(zone)
    # A bare weekday or "tomorrow" with no time -> 9 am rather than "now"
    has_time = re.search(r"\d|noon|midnight|morning|afternoon|evening|tonight|minute|hour", when.lower())
    if not has_time:
        dt = dt.replace(hour=9, minute=0, second=0, microsecond=0)
    return dt.replace(second=0, microsecond=0)


def spoken(dt, now=None):
    """Friendly phrasing: 'today at 3:15 PM', 'Friday, Nov 6 at 9:00 AM'."""
    now = now or datetime.now(dt.tzinfo)
    clock = dt.strftime("%I:%M %p").lstrip("0")
    days = (dt.date() - now.date()).days
    if days == 0:
        return f"today at {clock}"
    if days == 1:
        return f"tomorrow at {clock}"
    return f"{dt.strftime('%A, %B')} {dt.day} at {clock}"
