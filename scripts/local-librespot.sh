#!/usr/bin/env bash
# Start librespot locally for development/testing.
# Requires: brew install librespot

set -euo pipefail

FIFO_PATH="${FIFO_PATH:-/tmp/spotify.fifo}"
DEVICE_NAME="${DEVICE_NAME:-PyJockie}"
BITRATE="${BITRATE:-320}"

# Create FIFO if it doesn't exist
if [ ! -p "$FIFO_PATH" ]; then
    echo "Creating FIFO at $FIFO_PATH"
    mkfifo "$FIFO_PATH"
fi

echo "Starting librespot as '$DEVICE_NAME' (bitrate: $BITRATE)"
echo "Select '$DEVICE_NAME' in your Spotify app to start streaming."
exec librespot \
    --name "$DEVICE_NAME" \
    --backend pipe \
    --device "$FIFO_PATH" \
    --bitrate "$BITRATE" \
    --format S16
