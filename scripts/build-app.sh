#!/usr/bin/env bash
# Build PyJockie.app using py2app.
# Copies bundled binaries (librespot, ffmpeg, libopus) into the .app bundle.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "==> Cleaning previous build..."
rm -rf build dist

echo "==> Building .app with py2app..."
python setup.py py2app 2>&1

echo "==> Copying bundled binaries..."
RESOURCES="dist/PyJockie.app/Contents/Resources"

# Copy librespot
LIBRESPOT="$(which librespot)"
echo "    librespot: $LIBRESPOT"
cp "$LIBRESPOT" "$RESOURCES/librespot"
chmod +x "$RESOURCES/librespot"

# Copy ffmpeg
FFMPEG="$(which ffmpeg)"
echo "    ffmpeg: $FFMPEG"
cp "$FFMPEG" "$RESOURCES/ffmpeg"
chmod +x "$RESOURCES/ffmpeg"

# Copy libopus
LIBOPUS="/opt/homebrew/lib/libopus.dylib"
if [ -f "$LIBOPUS" ]; then
    echo "    libopus: $LIBOPUS"
    cp "$LIBOPUS" "$RESOURCES/libopus.dylib"
else
    echo "    WARNING: libopus not found at $LIBOPUS"
fi

echo ""
echo "==> Build complete!"
echo "    App: dist/PyJockie.app"
du -sh "dist/PyJockie.app"
echo ""
echo "    To install: cp -r dist/PyJockie.app /Applications/"
