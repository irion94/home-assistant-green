# Phase 2 – DevOps Prompt for Claude Code / Codex

ROLE: You are my DevOps assistant for Home Assistant Green (HAOS). We work in a “project‑based” manner inside a repository containing the `config/` folder (GitOps). Do not edit anything through the UI. Always generate code-only outputs: files, diffs, folder structures, commands. Always provide exact paths.

## CONTEXT / GOAL
I want to:
1) Set up **GitHub → Home Assistant Green deploy** (primary: **Git Pull Add-on** via **webhook**, fallback: **SSH+rsync**).  
2) Configure **backups**:  
   - automatic **pre-deploy backup**,  
   - nightly scheduled backup (e.g. 03:15),  
   - optional CI artifact of the config directory (excluding DB & .storage).  
3) Prepare “as-code” **framework for official integrations** (Tuya, Xiaomi/Aqara, Daikin Onecta, Solarman Smart, etc.).  
4) Add `.gitignore` and a CI configuration check.  
5) Keep everything in clean “enterprise hygiene” (README, folder structure, secrets, workflows).

Repository base layout:
```
/config
  configuration.yaml
  automations.yaml
  packages/
  custom_components/
.github/workflows/
scripts/
```

## ASSUMPTIONS / CONSTRAINTS
- Device: **Home Assistant Green (HAOS)**.
- Deploy #1 (preferred): Git Pull Add-on + webhook → pull on `main` → config check → restart.
- Deploy #2 (fallback): SSH + rsync → `/config`.
- Backups use modern `backup.create` (fallback allowed).
- Never commit database files or `.storage/`.
- Secrets go in local `config/secrets.yaml` and CI uses GitHub Secrets.
- Do not rely on UI-based configuration. Use placeholders / stubs / examples only.

## TASKS TO GENERATE

### 1) `.gitignore`
Generate a full `.gitignore` including:
- `.storage/`, database files (`home-assistant_v2.db*`, `*.db-shm`, `*.db-wal`),
- `deps/`, `.cloud/`, `.HA_VERSION`, `__pycache__/`, `*.pyc`,
- `node_modules/`, `.env*`,
- `secrets.yaml` (but keep `secrets.yaml.example`),
- CI artifacts folder (optional), logs, temporary files.

### 2) CI workflow
Create `.github/workflows/ci.yml` that:
- runs on push + PR,
- uses `frenck/action-home-assistant@v2` to run `check_config` for `./config`,
- injects secrets using the `secrets:` block.

### 3) Deploy Method A: Git Pull + Webhook
Provide:
- `scripts/deploy_via_webhook.sh`
- `.github/workflows/deploy-webhook.yml`
- automation in `config/automations.yaml`:
  - trigger via webhook `<ID>`
  - run `homeassistant.check_config`
  - restart Home Assistant on success
  - send persistent notification
- additions to `configuration.yaml` if needed
- instructions/comment for Git Pull Add-on setup

Acceptance: pushing to `main` triggers workflow → webhook → Git Pull Add-on pulls changes → config check → restart.

### 4) Deploy Method B: SSH + rsync
Provide:
- `scripts/deploy_via_ssh.sh`
- `.github/workflows/deploy-ssh.yml` with filters for `config/**`
- requires GitHub Secrets: `HA_HOST`, `HA_SSH_USER`, `HA_SSH_KEY`, `HA_SSH_PORT`
- ensure database files are excluded
- workflow_dispatch support

### 5) Backups (pre-deploy + nightly)
Add to automations:
- `automation.pre_deploy_backup` triggered externally (webhook)
- `automation.nightly_backup` scheduled at 03:15
Use:
- `backup.create`
- optional retention via `backup.purge`

Include CI optional job to upload config artifacts (excluding DB/.storage).

### 6) Integrations – checklists & stubs
Prepare `secrets.yaml.example` with placeholders for:
- Tuya, Xiaomi Cloud, Aqara, Daikin Onecta, Solarman Smart, MQTT credentials

Add stubs in `config/packages/`:
- `tuya.yaml`
- `onecta.yaml`
- `mqtt.yaml`
- `discovery.yaml`
- explain UI-based steps in comments
- include example template sensors/entities

### 7) Discovery / Device Scanning
Ensure comments/snippets for enabling:
- `zeroconf`, `ssdp`, `dhcp`, `bluetooth`
Create `packages/discovery.yaml` with helpers for event logging (`homeassistant_start`, `device_registry_updated`).

### 8) README.md updates
Add sections:
- Deploy (Git Pull + SSH)
- Backup strategy
- Integration onboarding
- Rollback instructions
- Required GitHub Secrets

## OUTPUT FORMAT
Return:
- List of files + single-sentence purpose
- Under each: **full snippet or diff** ready to copy/paste
- No narrative text outside the strict structure

## ACCEPTANCE CRITERIA
- `git push main` → CI runs, deploy triggers, config checks pass, instance restarts automatically
- Pre-deploy backup webhook works
- Nightly backup runs
- Repo contains no DB / `.storage`
- Integrations have clear stubs & placeholder secrets
- README includes deploy/backup/runbook sections
