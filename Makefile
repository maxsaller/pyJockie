# PyJockie — macOS menu bar Spotify-to-Discord streamer
# Requires: uv, brew install librespot ffmpeg opus

PYTHON     := .venv/bin/python
UV         := uv
APP_NAME   := PyJockie
APP_BUNDLE := dist/$(APP_NAME).app
RESOURCES  := $(APP_BUNDLE)/Contents/Resources

.PHONY: help install sync build clean run dev install-app check patch-py2app icon

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Create venv and install all dependencies
	$(UV) sync

sync: install ## Alias for install

patch-py2app: ## Patch py2app zlib bug for uv-managed Python
	@$(PYTHON) scripts/patch-py2app.py

icon: ## Compile .icon into Assets.car + .icns (requires Xcode)
	@echo "==> Compiling icon with actool..."
	@xcrun actool pyJockie.icon \
		--app-icon pyJockie \
		--compile resources \
		--output-partial-info-plist /dev/null \
		--minimum-deployment-target 26.0 \
		--platform macosx \
		--target-device mac
	@echo "  Generated Assets.car + pyJockie.icns"

build: install patch-py2app icon ## Build PyJockie.app bundle
	@echo "==> Cleaning previous build..."
	rm -rf build dist
	@echo "==> Building .app with py2app..."
	$(PYTHON) setup.py py2app > build.log 2>&1 || (tail -5 build.log; exit 1)
	@echo "==> Copying bundled binaries..."
	cp "$$(which librespot)" "$(RESOURCES)/librespot"
	chmod +x "$(RESOURCES)/librespot"
	cp "$$(which ffmpeg)" "$(RESOURCES)/ffmpeg"
	chmod +x "$(RESOURCES)/ffmpeg"
	cp resources/Assets.car "$(RESOURCES)/Assets.car"
	@if [ -f /opt/homebrew/lib/libopus.dylib ]; then \
		cp /opt/homebrew/lib/libopus.dylib "$(RESOURCES)/libopus.dylib"; \
		echo "  Copied libopus"; \
	else \
		echo "  WARNING: libopus not found at /opt/homebrew/lib/libopus.dylib"; \
	fi
	@echo ""
	@echo "==> Build complete: $(APP_BUNDLE)"
	@du -sh "$(APP_BUNDLE)"

clean: ## Remove build artifacts
	rm -rf build dist *.egg-info .eggs build.log

run: install ## Run the menu bar app (development)
	$(UV) run python app.py

dev: install ## Run the bot only (headless, reads .env)
	@if [ -f .env ]; then set -a && . ./.env && set +a; fi && \
	$(UV) run python -m bot.main

install-app: build ## Build and copy to /Applications
	cp -r "$(APP_BUNDLE)" /Applications/
	@echo "Installed to /Applications/$(APP_NAME).app"

check: ## Verify system dependencies
	@echo "Checking dependencies..."
	@which librespot >/dev/null 2>&1 && echo "  librespot: OK" || echo "  librespot: MISSING (brew install librespot)"
	@which ffmpeg >/dev/null 2>&1 && echo "  ffmpeg: OK" || echo "  ffmpeg: MISSING (brew install ffmpeg)"
	@test -f /opt/homebrew/lib/libopus.dylib && echo "  libopus: OK" || echo "  libopus: MISSING (brew install opus)"
	@$(UV) --version >/dev/null 2>&1 && echo "  uv: OK ($$($(UV) --version))" || echo "  uv: MISSING (brew install uv)"
