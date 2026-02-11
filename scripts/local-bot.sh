#!/usr/bin/env bash
# Start the Discord bot locally for development/testing.
# Requires: uv, .env file with DISCORD_TOKEN

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load .env
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
else
    echo "Error: .env file not found at $PROJECT_DIR/.env"
    exit 1
fi

export FIFO_PATH="${FIFO_PATH:-/tmp/spotify.fifo}"
export EVENT_PORT="${EVENT_PORT:-8080}"

# Ensure venv exists
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "Creating virtual environment..."
    uv venv "$PROJECT_DIR/.venv"
    uv pip install -r "$PROJECT_DIR/bot/requirements.txt"
fi

echo "Starting PyJockie bot..."
echo "FIFO: $FIFO_PATH | Event port: $EVENT_PORT"
exec "$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/bot/main.py"
