# Claude‑Code Debug Prompt — Home Assistant SSH + Config Check

ROLE: You are my **debug assistant**. You are allowed to run **local shell commands** I provide (copy/paste), and modify files in this repo. Your goal is to **locate and fix why `ha core check` fails** and ensure we can deploy/restart via SSH.

## CONTEXT
- Device: **Home Assistant Green (HAOS)**.
- SSH add‑on: **Advanced SSH & Web Terminal** — running and accessible.
- SSH details:
  - Host: "192.168.55.116"
  - Port: 22
  - User: "root"
  - Key: "~/.ssh/ha_green"
- Our repo has the config in `./config/` (already rsynced once).
- **Important**: When the `ha` CLI is run **without** `--config /config`, it defaults to `/root/.homeassistant` and fails. Always pass `--config /config`.

## OBJECTIVE
1) Verify that `/config` on the device contains our files and that `ha core check --config /config` passes.
2) If it fails, identify YAML errors or bad includes (especially `!include_dir_named packages`).
3) Ensure we can deploy via rsync and then validate and restart.

## DIAGNOSTIC COMMANDS (run locally in a terminal by copy/paste)
> Replace nothing — values are already correct.

```bash
# 0) Basic info & verify we hit the right box
ssh -i ~/.ssh/ha_green -p 22 root@192.168.55.116 "echo OK && ha core info"

# 1) What is /config and what is inside?
ssh -i ~/.ssh/ha_green -p 22 root@192.168.55.116 "ls -la /config && ls -la /homeassistant && head -n 40 /config/configuration.yaml || true"

# 2) Always run check with explicit config path
ssh -i ~/.ssh/ha_green -p 22 root@192.168.55.116 "ha core check --config /config"

# 3) If still failing, dump logs to see parser issues
ssh -i ~/.ssh/ha_green -p 22 root@192.168.55.116 "grep -n \"include_dir\" -n /config/configuration.yaml || true"
ssh -i ~/.ssh/ha_green -p 22 root@192.168.55.116 "find /config -maxdepth 2 -type f -name '*.yaml' -print"

# 4) Sanity check YAML locally (ignoring HA custom tags)
python3 - << 'PY'
import sys, yaml, pathlib
p = pathlib.Path('config/configuration.yaml')
print('Exists:', p.exists(), 'Size:', p.stat().st_size if p.exists() else 0)
class IgnoreTagsLoader(yaml.SafeLoader):
    pass
def unknown(loader, node):
    return "IGNORED_CUSTOM_TAG"
IgnoreTagsLoader.add_constructor(None, unknown)
print('NOTE: Local YAML parse ignores HA custom tags (e.g. !include_dir_*)')
print('Load OK:', yaml.load(p.read_text(), Loader=IgnoreTagsLoader) is not None)
PY
```

## COMMON FIXES TO TRY (make minimal changes, then re‑rsync)
- **Make sure comments in YAML use `#`, not `//`.**
- `packages: !include_dir_named packages` is valid for HA — keep a **space** between the tag and the directory name.
- Ensure `config/packages/` exists and contains at least one valid `.yaml` file.
- If you still see parser errors about `!include_dir_named`, replace with the merge variant and adjust structure:
  ```yaml
  homeassistant:
    packages: !include_dir_merge_named packages
  ```
  Then verify the package files are mappings (top-level keys).

## REDEPLOY + RESTART (from repo root)
```bash
# Sync only config (exclude runtime)
rsync -avz \
  -e "ssh -i ~/.ssh/ha_green -p 22 -o StrictHostKeyChecking=no" \
  --exclude '.storage' \
  --exclude 'home-assistant_v2.db*' \
  --exclude '*.db-shm' \
  --exclude '*.db-wal' \
  ./config/ root@192.168.55.116:/config/

# Validate and restart (explicit config path)
ssh -i ~/.ssh/ha_green -p 22 -o StrictHostKeyChecking=no \
  root@192.168.55.116 "ha core check --config /config && ha core restart"
```

## ACCEPTANCE CRITERIA
- `ha core check --config /config` returns **success** (no "File configuration.yaml not found").
- After rsync, `ls -la /config` shows our `configuration.yaml` and `packages/`.
- `ha core restart` completes without error.
