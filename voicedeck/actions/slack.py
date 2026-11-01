"""Post to and read from Slack with a bot token (free Slack Web API)."""
import os


class Slack:
    def __init__(self, cfg):
        from slack_sdk import WebClient
        s = cfg.get("slack", {}) or {}
        token = os.environ.get("SLACK_BOT_TOKEN", "")
        if not token.startswith("xoxb-") or "your-token" in token:
            raise RuntimeError("SLACK_BOT_TOKEN missing in .env")
        self.client = WebClient(token=token)
        self.default = s.get("default_channel", "general")
        self.channels = {str(k).lower(): v for k, v in (s.get("channels") or {}).items()}
        self._users = {}

    def resolve(self, name):
        """Spoken channel name -> channel ID."""
        name = (name or self.default).lower().lstrip("#").replace(" ", "-")
        if name in self.channels and not str(self.channels[name]).startswith("C0123"):
            return self.channels[name]
        cursor = None
        while True:  # look it up (needs channels:read)
            resp = self.client.conversations_list(limit=200, cursor=cursor,
                                                  exclude_archived=True)
            for ch in resp["channels"]:
                if ch["name"] == name:
                    self.channels[name] = ch["id"]
                    return ch["id"]
            cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                raise LookupError(f"I couldn't find a channel called {name}.")

    def post(self, channel, text):
        self.client.chat_postMessage(channel=self.resolve(channel), text=text)

    def _user(self, uid):
        if uid not in self._users:
            try:
                u = self.client.users_info(user=uid)["user"]
                self._users[uid] = u.get("real_name") or u.get("name") or "someone"
            except Exception:
                self._users[uid] = "someone"
        return self._users[uid]

    def recent(self, channel, limit=15):
        resp = self.client.conversations_history(channel=self.resolve(channel), limit=limit)
        lines = []
        for m in reversed(resp["messages"]):
            if m.get("subtype"):
                continue
            who = self._user(m["user"]) if m.get("user") else "a bot"
            lines.append(f"{who}: {m.get('text', '')}")
        return lines
