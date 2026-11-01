# Voice Deck

A voice-first assistant that runs **locally on a Raspberry Pi 5**, built entirely from free, open-source tools. Speak a command, and it posts to Slack, reads or adds Google Calendar events, sets reminders, or answers questions. Speech recognition, the language model, and the voice all run on the Pi.

```
 trigger ─▶ mic ─▶ Whisper ─▶ router ─┬─ regex (instant) ─┐
 (Enter /             (STT)           └─ Ollama LLM ──────┤
 wake word /                                              ▼
 button)                     Slack · Calendar · Reminders · Chat
                                                          │
                                  speaker ◀── Piper (TTS) ◀┘
```

## What you can say

| Say | It does |
|---|---|
| "Post to general, running late" | Reads it back, posts after you say **yes** |
| "What did I miss?" / "What did I miss in robotics?" | Summarizes recent Slack messages |
| "What's on my calendar today?" / "...for Friday" | Reads your events |
| "Put dentist on my calendar Friday at 3" | Reads it back, adds after **yes** |
| "Remind me in 20 minutes to check the oven" | Speaks a reminder when it's due |
| "Never mind" | Cancels |
| Anything else | Short spoken answer from the local model |

Anything that sends or changes something (Slack posts, calendar events) is always confirmed out loud first.

## Hardware

- Raspberry Pi 5 (8GB or 16GB) running **64-bit** Raspberry Pi OS
- A USB microphone, or a ReSpeaker mic array for noisy rooms and cars
- A speaker (USB, Bluetooth, or 3.5mm through a USB sound card)
- Optional: a push button between **GPIO17** and **GND**
- Recommended: an active cooler and an SSD

## Quick start

```bash
git clone <your-repo-url> voice-deck   # or unzip the download
cd voice-deck
chmod +x install.sh scripts/*.sh
./install.sh
```

The installer sets up Ollama, the `qwen3:1.7b` model, Whisper, Piper, and a Python environment. It takes about 10–20 minutes the first time.

**Test by typing first** (no mic needed):

```bash
.venv/bin/python -m voicedeck --text
```

**Then test with your voice** (press Enter, speak, and pause when you're done):

```bash
.venv/bin/python -m voicedeck
```

If it can't hear you, run `.venv/bin/python -m voicedeck --list-devices` and set `input_device` in `config.yaml` to your mic's number.

## Connect Slack

1. Go to **api.slack.com/apps**, choose **Create New App**, then **From scratch**, and pick your workspace.
2. Under **OAuth & Permissions**, add these **Bot Token Scopes**: `chat:write`, `channels:read`, `channels:history`, `users:read`.
3. Click **Install to Workspace** and copy the **Bot User OAuth Token** (it starts with `xoxb-`).
4. Paste it into `.env` as `SLACK_BOT_TOKEN=xoxb-...`
5. In each channel you want to use, type `/invite @YourAppName`.
6. Optional: put channel IDs in `config.yaml` under `slack.channels`. If you skip this, channels are looked up by name.

For private channels, also add `groups:read` and `groups:history`.

## Connect Google Calendar

1. Go to **console.cloud.google.com** and create a project.
2. Under **APIs & Services**, then **Library**, enable the **Google Calendar API**.
3. Under **OAuth consent screen**, choose **External** and add yourself as a **test user**.
4. Under **Credentials**, choose **Create credentials**, then **OAuth client ID**, with type **Desktop app**. Download the JSON file and save it in this folder as `credentials.json`.
5. Run:
   ```bash
   .venv/bin/python scripts/setup_google.py              # Pi with a desktop
   .venv/bin/python scripts/setup_google.py --headless   # over SSH, see the script header
   ```

## Hands-free modes

In `config.yaml`, set `trigger:` to one of:

- `keyboard`: press Enter (the default, best for testing)
- `gpio`: press a physical button on GPIO17
- `wakeword`: say "Hey Jarvis". First run `./install.sh --wakeword`. The built-in wake words are for **non-commercial use only**; you can train your own for free with openWakeWord.

To start at boot, run `./scripts/install-service.sh`. Logs are in `journalctl -u voicedeck -f`.

## Tuning speed and accuracy

| Setting | Faster | More accurate |
|---|---|---|
| `stt.model` | `tiny.en` | `base.en` / `small.en` |
| `llm.model` | `qwen3:0.6b` | `qwen3:4b` |

Common phrasings skip the language model entirely (see `voicedeck/router.py`), so they respond almost instantly. To make a phrasing fast, add a regex for it there.

## Project layout

```
voice-deck/
├── install.sh               one-command setup
├── config.example.yaml      settings (copied to config.yaml)
├── .env.example             secrets (copied to .env)
├── voicedeck/
│   ├── __main__.py          entry point: python -m voicedeck
│   ├── assistant.py         main loop + intent handlers
│   ├── router.py            regex fast path + LLM fallback
│   ├── llm.py               Ollama client
│   ├── stt.py               faster-whisper speech-to-text
│   ├── tts.py               Piper text-to-speech
│   ├── audio.py             mic capture, silence detection, beeps
│   ├── triggers.py          Enter key / wake word / GPIO button
│   ├── timeparse.py         "tomorrow at 3 p.m." -> datetime
│   └── actions/
│       ├── slack.py
│       ├── gcal.py
│       └── reminders.py
├── scripts/
│   ├── setup_google.py      one-time Google sign-in
│   └── install-service.sh   run at boot
└── tests/                   pytest tests (no hardware needed)
```

Run the tests with `.venv/bin/pip install pytest && .venv/bin/python -m pytest`.

## Open-source stack

| Part | Tool | License |
|---|---|---|
| LLM runtime | Ollama | MIT |
| Model | Qwen3 | Apache 2.0 |
| Speech-to-text | faster-whisper | MIT |
| Text-to-speech | Piper | MIT (newer releases GPL-3.0) |
| Wake word | openWakeWord | Apache 2.0 (code) |
| Date parsing | dateparser | BSD |

Slack and Google Calendar are closed services, but their APIs are free to use. To make the whole stack open, you could swap them for Matrix/Mattermost and a CalDAV server like Radicale.

## Roadmap

- [ ] Interrupt replies by talking ("stop")
- [ ] Queue Slack posts and calendar changes when offline, then send when back online
- [ ] Wrist remote: Arduino Nano ESP32 + INMP441 mic that streams audio to the Pi
- [ ] Car mode: 12V power with ignition-sense shutdown, steering-wheel button through a CAN bus (MCP2515)
- [ ] Custom wake word
