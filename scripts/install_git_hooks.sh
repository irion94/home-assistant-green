#!/usr/bin/env bash
set -euo pipefail

# Configure this repo to use hooks from .githooks/

git config core.hooksPath .githooks
chmod +x .githooks/* || true
echo "[hooks] Installed. Git now uses hooks from .githooks/."

