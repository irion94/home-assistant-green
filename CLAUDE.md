# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Home Assistant Enterprise Starter is a batteries-included template for project-style Home Assistant deployments (Home Assistant OS/Green). It provides:
- Git-based configuration management (`/config`) with CI validation
- A custom integration scaffold (`custom_components/enterprise_example`)
- Two deployment strategies: Git Pull webhook and SSH/rsync
- Safe deployment workflow: validate → sync → restart

## Build, Test, and Development Commands

### Local Development
```bash
# Install test dependencies
pip install -e .[test]

# Run tests (pytest with async support)
pytest -q

# Validate Home Assistant configuration via Docker
docker run --rm -v "$PWD/config":/config ghcr.io/home-assistant/home-assistant:stable \
  python -m homeassistant --script check_config --config /config
```

### Deployment
```bash
# Deploy via webhook (requires WEBHOOK_URL env var)
./scripts/deploy_via_webhook.sh

# Deploy via SSH/rsync (requires HA_HOST, HA_SSH_USER, HA_SSH_KEY env vars)
./scripts/deploy_via_ssh.sh
```

## Architecture

### Custom Integration Structure
The repository demonstrates a typical Home Assistant custom component:
- `config/custom_components/enterprise_example/` — Custom integration module
  - `__init__.py` — Integration setup (`async_setup`, `async_setup_entry`)
  - `const.py` — Domain constants (`DOMAIN = 'enterprise_example'`)
  - `sensor.py` — Platform implementation using `SensorEntity`
  - `services.yaml` — Service definitions (if any)

Custom integrations follow the Home Assistant component pattern:
1. `async_setup()` for YAML-based configuration
2. `async_setup_entry()` for UI-based config flow (not implemented in template)
3. Platform files (`sensor.py`, etc.) register entities via `async_setup_platform()`

### Configuration Layout
- `config/configuration.yaml` — Main HA config with package imports
- `config/packages/` — Feature-scoped YAML configurations merged into main config
- `config/automations.yaml` — Automation definitions
- `config/secrets.yaml.example` — Template for secret values (actual `secrets.yaml` is gitignored)

The packages pattern allows modular organization: each package file is a complete HA configuration snippet that gets merged at load time.

### Deployment Workflows
Two deployment strategies exist in `.github/workflows/`:

1. **Git Pull + Webhook** (`deploy-webhook.yml`) — For HAOS/Green
   - HA Git Pull add-on pulls changes from repository
   - GitHub workflow triggers webhook to restart HA
   - No SSH access needed

2. **SSH + rsync** (`deploy-ssh.yml`) — For systems with SSH
   - rsync syncs only changed files to `/config`
   - Runs `ha core check` before restart
   - Executes `ha core restart` via SSH

Both exclude `.storage/` and `home-assistant_v2.db*` to prevent overwriting runtime state.

## Coding Standards

### Python (Custom Integration)
- Python 3.11+ required
- Follow PEP 8: 4-space indents, snake_case for modules/functions
- Use type hints from `__future__ import annotations` (Home Assistant pattern)
- Entity classes inherit from `SensorEntity`, `BinarySensorEntity`, etc.
- Use `_attr_*` class attributes for static properties when possible

### YAML Configuration
- 2-space indentation
- Reference secrets via `!secret key_name` (never commit actual secrets)
- Use `!include` and `!include_dir_named` for modularity
- Package files should be self-contained feature configurations

### Testing
- Framework: pytest with pytest-asyncio
- All test files in `tests/` directory
- Use `pytest.mark.asyncio` for async tests
- CI runs both config validation and pytest

## Commit Conventions
Use Conventional Commits format:
- `feat: add new sensor platform`
- `fix: handle None state in sensor`
- `config: update automation trigger`
- `ci: update deployment workflow`

## Important Notes

### Security
- Never commit `secrets.yaml`, `.storage/`, or `home-assistant_v2.db*`
- Use GitHub Secrets for CI/CD credentials (webhook URLs, SSH keys)
- Review deployment workflow targets before enabling

### Configuration Changes
- Always validate config before deployment using Docker check command
- Test custom integration changes with `pytest` before pushing
- CI must pass (config validation + tests) before merging

### Custom Integration Development
- The template integration is a minimal scaffold — expand as needed
- To add platforms: create `sensor.py`, `binary_sensor.py`, etc.
- To add services: define in `services.yaml` and implement in `__init__.py`
- For config flow (UI setup), implement `config_flow.py` and update `async_setup_entry()`
