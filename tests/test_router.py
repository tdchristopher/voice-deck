from voicedeck.router import route


def r(text):
    i = route(text, llm=None)
    return i.name, i.slots


def test_slack_post_variants():
    assert r("Post to general, running late.") == ("slack_post", {"channel": "general", "message": "running late."})
    assert r("send to #design: mockups are ready")[1] == {"channel": "design", "message": "mockups are ready"}
    assert r("Message the robotics channel saying meeting moved to 5")[1] == \
        {"channel": "robotics", "message": "meeting moved to 5"}


def test_catchup():
    assert r("What did I miss?") == ("slack_catchup", {})
    assert r("what did I miss in random") == ("slack_catchup", {"channel": "random"})


def test_calendar_day():
    assert r("What's on my calendar today?") == ("calendar_day", {"day": "today"})
    assert r("check my schedule for Friday") == ("calendar_day", {"day": "Friday"})
    assert r("What's my calendar?") == ("calendar_day", {})
    assert r("what do I have tomorrow") == ("calendar_day", {"day": "tomorrow"})


def test_reminders():
    assert r("Remind me to call mom in 10 minutes.") == \
        ("reminder", {"message": "call mom", "when": "in 10 minutes"})
    assert r("remind me in an hour to feed the cats") == \
        ("reminder", {"message": "feed the cats", "when": "in an hour"})
    assert r("Remind me to check the bees tomorrow at 9 a.m.") == \
        ("reminder", {"message": "check the bees", "when": "tomorrow at 9 a.m"})


def test_cancel_and_unknown():
    assert r("never mind")[0] == "cancel"
    assert r("how tall is mount everest")[0] == "unknown"  # no LLM in tests
    assert r("")[0] == "unknown"


def test_llm_fallback():
    class FakeLLM:
        def chat_json(self, system, user, schema):
            return {"intent": "calendar_add", "title": "Dentist", "when": "thursday at 10 am"}
    i = route("put dentist on my calendar thursday at 10", FakeLLM())
    assert (i.name, i.source) == ("calendar_add", "llm")
    assert i.slots == {"title": "Dentist", "when": "thursday at 10 am"}
