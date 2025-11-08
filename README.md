# Home Assistant — Enterprise Starter

This repository is a batteries-included starter for **project-style** work with Home Assistant
(e.g. for a Home Assistant Green running Home Assistant OS). It gives you:

- Git-based config (`/config`) with CI validation
- A `custom_components/enterprise_example` integration scaffold
- Two deployment options:
  1. **Webhook to Git Pull add-on** (`deploy_via_webhook.sh` / workflow `deploy-webhook.yml`)
  2. **SSH + rsync** to `/config` (`deploy_via_ssh.sh` / workflow `deploy-ssh.yml`)
- Safe restart flow: validate config → restart core

> ⚠️ For **Home Assistant Green / HAOS** you don't have shell/SSH by default.
> Install **Terminal & SSH add-on** if you want SSH/rsync deployments.
> For GitOps-style, install **Git pull add-on** and configure a webhook.

## Quick start

1. Fork this repo.
2. Choose deployment method:

### A) Git Pull add-on + webhook (recommended for Green)

- Install **Git pull** add-on and point it at this repository (read-only deploy key).
- Configure a **webhook** (secret token) that triggers `git pull` and optional restart.
- Put the webhook URL as `WEBHOOK_URL` GitHub Secret, and the restart command/action if needed.

### B) SSH + rsync

- Install **Terminal & SSH add-on**.
- Create SSH key pair; add public key to the add-on.
- Set GitHub Secrets: `HA_HOST`, `HA_SSH_USER`, `HA_SSH_KEY`, `HA_SSH_PORT` (optional).
- The workflow will `rsync` only changed files to `/config`, run `ha core check`, then `ha core restart`.

## Local development

- Run config checks in Docker:

```bash
docker run --rm -v "$PWD/config":/config ghcr.io/home-assistant/home-assistant:stable   python -m homeassistant --script check_config --config /config
```

- Test the custom integration:

```bash
pip install -e .[test]
pytest -q
```

## Layout

```
config/
  configuration.yaml
  automations.yaml
  packages/
  custom_components/enterprise_example/
scripts/
.github/workflows/
tests/
```

## Notes

- Keep secrets out of Git; use `secrets.yaml` locally. In CI, provide env vars / GitHub Secrets.
- When using Git Pull add-on, avoid pushing the database and `.storage`.
- For HACS distribution of the custom integration, publish the integration in its own repo or add this repo as a custom repository.
