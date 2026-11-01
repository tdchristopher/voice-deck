"""Read and add Google Calendar events (free Google Calendar API)."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from ..config import resolve_path

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


class Calendar:
    def __init__(self, cfg):
        c = cfg.get("calendar", {}) or {}
        self.cal_id = c.get("calendar_id", "primary")
        self.tz = c.get("timezone", "America/Los_Angeles")
        self.default_minutes = c.get("default_duration_minutes", 30)
        self.token_path = resolve_path(cfg, "data/google_token.json")
        if not self.token_path.exists():
            raise RuntimeError("Google not connected. Run: .venv/bin/python scripts/setup_google.py")
        self._svc = None

    def _service(self):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
        if not creds.valid and creds.refresh_token:
            creds.refresh(Request())
            self.token_path.write_text(creds.to_json())
        if self._svc is None or not creds.valid:
            self._svc = build("calendar", "v3", credentials=creds, cache_discovery=False)
        return self._svc

    def events_on(self, day):
        zone = ZoneInfo(self.tz)
        start = datetime.combine(day, datetime.min.time(), zone)
        end = start + timedelta(days=1)
        resp = self._service().events().list(
            calendarId=self.cal_id, timeMin=start.isoformat(), timeMax=end.isoformat(),
            singleEvents=True, orderBy="startTime", maxResults=20).execute()
        out = []
        for e in resp.get("items", []):
            s = e["start"]
            if "dateTime" in s:
                t = datetime.fromisoformat(s["dateTime"]).astimezone(zone)
                when = t.strftime("%I:%M %p").lstrip("0")
            else:
                when = "all day"
            out.append((when, e.get("summary", "(no title)")))
        return out

    def add(self, title, start, minutes=None):
        end = start + timedelta(minutes=minutes or self.default_minutes)
        body = {
            "summary": title,
            "start": {"dateTime": start.isoformat(), "timeZone": self.tz},
            "end": {"dateTime": end.isoformat(), "timeZone": self.tz},
        }
        return self._service().events().insert(calendarId=self.cal_id, body=body).execute()
