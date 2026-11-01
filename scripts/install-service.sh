#!/usr/bin/env bash
# Start Voice Deck automatically at boot (systemd).
# Requires trigger: wakeword or gpio in config.yaml (there's no keyboard at boot).
set -euo pipefail
DIR="$(cd "$(dirname "$0")/.." && pwd)"
USER_NAME="$(whoami)"

if grep -qE '^trigger:\s*keyboard' "$DIR/config.yaml" 2>/dev/null; then
  echo "Set 'trigger: wakeword' or 'trigger: gpio' in config.yaml first."
  exit 1
fi

sudo tee /etc/systemd/system/voicedeck.service >/dev/null <<EOF
[Unit]
Description=Voice Deck assistant
After=network-online.target sound.target ollama.service
Wants=network-online.target

[Service]
User=$USER_NAME
WorkingDirectory=$DIR
ExecStart=$DIR/.venv/bin/python -m voicedeck
Restart=on-failure
RestartSec=5
Environment=PYTHONUNBUFFERED=1
SupplementaryGroups=audio gpio

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now voicedeck
echo "Running. Logs: journalctl -u voicedeck -f"
