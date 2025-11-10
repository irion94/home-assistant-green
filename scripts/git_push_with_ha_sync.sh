#!/usr/bin/env bash
set -euo pipefail

# Push wrapper that always prioritizes HA state before pushing to remote.
# Steps:
#  1) Sync HA -> repo (GUI-only by default)
#  2) If sync produced changes, auto-commit and ABORT push (exit 1)
#     so you can review/adjust and re-run the push explicitly.
#  3) If no changes from sync, run `git push` with passed arguments.
#
# Modes:
#  --mode gui         : pull automations.yaml/scripts.yaml/scenes.yaml (default)
#  --mode components  : pull custom_components + www/community
#  --mode full        : safe merge of full /config into ./config (no delete)
#  --allow-push       : if a commit was created by sync, still proceed to push
#  --no-commit        : do not auto-commit; just stage nothing and abort on changes
#
# Environment:
#  Requires HA_HOST, HA_SSH_USER, HA_SSH_KEY; optional HA_SSH_PORT.
#

MODE="gui"
ALLOW_PUSH=false
NO_COMMIT=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)
      MODE="$2"; shift 2 ;;
    --allow-push)
      ALLOW_PUSH=true; shift ;;
    --no-commit)
      NO_COMMIT=true; shift ;;
    -h|--help)
      echo "Usage: $0 [--mode gui|components|full] [--allow-push] [--no-commit] -- [git push args...]"; exit 0 ;;
    --)
      shift; break ;;
    *) break ;;
  esac
done

# Remaining args passed to git push
PUSH_ARGS=("$@")

require_env() {
  : "${HA_HOST:?Missing HA_HOST}"
  : "${HA_SSH_USER:?Missing HA_SSH_USER}"
  : "${HA_SSH_KEY:?Missing HA_SSH_KEY}"
}

run_sync() {
  case "$MODE" in
    gui)
      echo "[push-with-sync] Syncing GUI-managed files from HA..."
      require_env
      ./scripts/pull_gui_changes.sh ;;
    components)
      echo "[push-with-sync] Syncing components (custom_components + HACS) from HA..."
      require_env
      ./scripts/sync_from_ha.sh --components-only --into-config ;;
    full)
      echo "[push-with-sync] Safe merging full HA config into ./config ..."
      require_env
      ./scripts/sync_from_ha.sh --into-config ;;
    *)
      echo "Unknown mode: $MODE" >&2; exit 2 ;;
  esac
}

has_changes() {
  test -n "$(git status --porcelain)"
}

auto_commit() {
  if [[ "$NO_COMMIT" == true ]]; then
    return 0
  fi
  git add -A
  if git diff --cached --quiet; then
    return 0
  fi
  TS=$(date +%Y-%m-%dT%H:%M:%S)
  git commit -m "chore(sync): import HA changes (${TS})" || true
}

run_sync

if has_changes; then
  echo "[push-with-sync] Changes detected after sync. Prioritizing HA state."
  auto_commit
  if [[ "$ALLOW_PUSH" == true ]]; then
    echo "[push-with-sync] Proceeding to push with new sync commit(s)."
  else
    echo "[push-with-sync] Aborting push to let you review the sync commit(s)."
    echo "[push-with-sync] Tip: re-run with --allow-push to continue automatically."
    exit 1
  fi
fi

echo "[push-with-sync] Running: git push ${PUSH_ARGS[*]:-}" 
git push "${PUSH_ARGS[@]:-}"
echo "[push-with-sync] Done."

