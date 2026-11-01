"""One-time Google Calendar sign-in. Saves data/google_token.json.

On a Pi with a desktop:   .venv/bin/python scripts/setup_google.py
Over SSH (no desktop):    .venv/bin/python scripts/setup_google.py --headless
  then on your laptop:    ssh -L 8765:localhost:8765 <user>@<pi-address>
  and open the printed link in your laptop's browser.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from google_auth_oauthlib.flow import InstalledAppFlow  # noqa: E402

from voicedeck.actions.gcal import SCOPES  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--headless", action="store_true", help="don't open a browser on the Pi")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()

    creds_file = ROOT / "credentials.json"
    if not creds_file.exists():
        sys.exit("Put your OAuth client file at credentials.json first (see README).")

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_file), SCOPES)
    creds = flow.run_local_server(port=args.port, open_browser=not args.headless)
    out = ROOT / "data" / "google_token.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(creds.to_json())
    print(f"Saved {out}. Google Calendar is connected.")


if __name__ == "__main__":
    main()
