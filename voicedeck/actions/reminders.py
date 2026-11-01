"""Local spoken reminders, saved to disk so they survive a restart."""
import json
import threading
import time
from datetime import datetime

from ..config import resolve_path


class Reminders:
    def __init__(self, cfg, on_due):
        self.path = resolve_path(cfg, (cfg.get("reminders", {}) or {}).get("file", "data/reminders.json"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.on_due = on_due
        self.lock = threading.Lock()
        self.items = json.loads(self.path.read_text()) if self.path.exists() else []
        threading.Thread(target=self._loop, daemon=True).start()

    def _save(self):
        self.path.write_text(json.dumps(self.items, indent=2))

    def add(self, when, message):
        with self.lock:
            self.items.append({"when": when.isoformat(), "message": message})
            self._save()

    def _loop(self):
        while True:
            due = []
            with self.lock:
                now = datetime.now().astimezone()
                keep = []
                for r in self.items:
                    (due if datetime.fromisoformat(r["when"]) <= now else keep).append(r)
                if due:
                    self.items = keep
                    self._save()
            for r in due:
                try:
                    self.on_due(r["message"])
                except Exception as e:
                    print(f"[reminders] {e}")
            time.sleep(5)
