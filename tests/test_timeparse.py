from datetime import datetime
from zoneinfo import ZoneInfo

from voicedeck.timeparse import parse_when, spoken

TZ = "America/Los_Angeles"
NOW = datetime(2026, 11, 4, 14, 0, tzinfo=ZoneInfo(TZ))  # Wednesday 2:00 PM


def p(s):
    return parse_when(s, TZ, now=NOW)


def test_relative():
    assert p("in 10 minutes") == NOW.replace(minute=10)
    assert p("in an hour") == NOW.replace(hour=15)


def test_clock_times():
    assert p("tomorrow at 3 p.m.") == datetime(2026, 11, 5, 15, 0, tzinfo=ZoneInfo(TZ))
    assert p("at noon tomorrow") == datetime(2026, 11, 5, 12, 0, tzinfo=ZoneInfo(TZ))
    assert p("tonight") == datetime(2026, 11, 4, 20, 0, tzinfo=ZoneInfo(TZ))


def test_weekdays():
    assert p("friday at 3 pm") == datetime(2026, 11, 6, 15, 0, tzinfo=ZoneInfo(TZ))
    assert p("next monday at 10 am") == datetime(2026, 11, 9, 10, 0, tzinfo=ZoneInfo(TZ))
    assert p("on Friday") == datetime(2026, 11, 6, 9, 0, tzinfo=ZoneInfo(TZ))


def test_garbage():
    assert p("banana") is None
    assert p("") is None


def test_spoken():
    assert spoken(NOW.replace(hour=15, minute=15), now=NOW) == "today at 3:15 PM"
    assert spoken(datetime(2026, 11, 6, 9, 0, tzinfo=ZoneInfo(TZ)), now=NOW) == "Friday, November 6 at 9:00 AM"
