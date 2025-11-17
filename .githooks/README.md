# Git Hooks for Home Assistant Sync

This directory contains custom git hooks for syncing changes FROM Home Assistant back to the repository before pushing.

## Purpose

These hooks serve a **different purpose** than pre-commit:

- **Pre-commit** (`.pre-commit-config.yaml`): Code quality checks, linting, formatting
- **Git hooks** (`.githooks/`): Sync HA-managed changes (GUI edits) back to repo before push

## Hooks

### `pre-push`

Syncs changes from Home Assistant to the repository before allowing a push. This ensures that any changes made through the Home Assistant UI (automations, scripts, scenes) are pulled back to the repo before you push new changes.

**Modes:**
- `gui` (default): Sync only GUI-managed files (automations.yaml, scripts.yaml, scenes.yaml)
- `components`: Sync custom components
- `full`: Full sync of entire config

**Environment Variables:**
- `HA_HOST`: Home Assistant host address
- `HA_SSH_USER`: SSH username
- `HA_SSH_KEY`: Path to SSH private key
- `HA_SSH_PORT`: SSH port (optional, default: 22)
- `HA_PREPUSH_MODE`: Sync mode (optional, default: gui)

## Installation

### Option 1: Enable HA Sync Hook (Optional)

If you want automatic syncing before every push:

```bash
./scripts/install_git_hooks.sh
```

This sets `core.hooksPath` to `.githooks/`, enabling the pre-push sync.

**Requirements:**
- Create `.env.local` at project root with HA connection details:
  ```bash
  HA_HOST=your-ha-host
  HA_SSH_USER=root
  HA_SSH_KEY=/path/to/ssh/key
  HA_PREPUSH_MODE=gui  # Optional
  ```

### Option 2: Use Pre-commit Only (Recommended for Most Users)

For code quality checks only (no HA sync):

```bash
pip install pre-commit
pre-commit install
```

This is recommended for contributors who don't have direct SSH access to the production HA instance.

## Workflow

When the pre-push hook is enabled and HA is configured:

1. You run `git push`
2. Hook syncs changes from HA → repo
3. If changes are detected:
   - Changes are auto-committed
   - Push is **aborted**
   - You review the sync commit
   - You re-run `git push`
4. If no changes, push proceeds normally

## Disabling

To disable the HA sync hook:

```bash
git config --unset core.hooksPath
```

Or point to standard hooks:

```bash
git config core.hooksPath .git/hooks
```

## Notes

- The sync hook is **optional** and only needed if you manage HA via SSH and want to keep the repo in sync
- Most users should just use pre-commit for code quality
- The hook safely skips sync if HA environment variables are not set
