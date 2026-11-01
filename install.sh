#!/usr/bin/env bash
# One-time setup for Voice Deck on Raspberry Pi OS (64-bit).
#   ./install.sh              core install
#   ./install.sh --wakeword   also install openWakeWord
set -euo pipefail
cd "$(dirname "$0")"

MODEL="${OLLAMA_MODEL:-qwen3:1.7b}"
VOICE="en_US-lessac-medium"
VOICE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium"
WAKEWORD=0
[[ "${1:-}" == "--wakeword" ]] && WAKEWORD=1

say() { printf "\n\033[1;36m==> %s\033[0m\n" "$*"; }

if [[ "$(uname -m)" != "aarch64" ]]; then
  echo "Warning: this isn't 64-bit ARM ($(uname -m)). On a Pi, install the 64-bit Raspberry Pi OS."
fi

say "Installing system packages"
sudo apt-get update
sudo apt-get install -y python3-venv python3-dev libportaudio2 portaudio19-dev alsa-utils curl

say "Installing Ollama"
if ! command -v ollama >/dev/null 2>&1; then
  curl -fsSL https://ollama.com/install.sh | sh
else
  echo "Ollama already installed."
fi

say "Downloading the language model ($MODEL) - this can take a few minutes"
ollama pull "$MODEL"

say "Creating Python environment"
# --system-site-packages lets us use the Pi's preinstalled gpiozero for button support
python3 -m venv --system-site-packages .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

say "Downloading Piper voice ($VOICE)"
mkdir -p voices data
for f in "$VOICE.onnx" "$VOICE.onnx.json"; do
  [[ -f "voices/$f" ]] || curl -fL -o "voices/$f" "$VOICE_URL/$f"
done

if [[ $WAKEWORD == 1 ]]; then
  say "Installing openWakeWord"
  if ! .venv/bin/pip install openwakeword; then
    # tflite-runtime has no wheels for newer Pythons; we only need the ONNX backend
    .venv/bin/pip install onnxruntime tqdm scipy scikit-learn requests
    .venv/bin/pip install --no-deps openwakeword
  fi
  .venv/bin/python -c "import openwakeword.utils as u; u.download_models(['hey_jarvis'])"
fi

say "Creating config files"
[[ -f config.yaml ]] || cp config.example.yaml config.yaml
[[ -f .env ]] || cp .env.example .env
if [[ "$MODEL" != "qwen3:1.7b" ]]; then
  sed -i "s/model: qwen3:1.7b/model: $MODEL/" config.yaml
fi

say "Done!"
cat <<EOF

Next steps:
  1. Test with typing (no mic needed):   .venv/bin/python -m voicedeck --text
  2. Test with your voice:               .venv/bin/python -m voicedeck
  3. Connect Slack:  put your bot token in .env  (see README)
  4. Connect Google Calendar:            .venv/bin/python scripts/setup_google.py
EOF
