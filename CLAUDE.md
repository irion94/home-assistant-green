# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a production Home Assistant deployment using GitOps workflow with:
- **Git-based configuration management** with automated CI/CD validation and deployment
- **Custom integrations**: Strava Coach (`config/custom_components/strava_coach/`)
- **Subproject**: Advanced Strava analytics (`ha-strava-coach/` - separate Python package)
- **Deployment**: Tailscale VPN + SSH/rsync for secure remote deployment
- **Testing**: 30% minimum test coverage (infrastructure), 70% target (full project)
- **Safe workflow**: validate → test → sync → deploy → health check → notify

## Build, Test, and Development Commands

### Local Development
```bash
# Install development dependencies (includes test, linting, type checking)
pip install -e .[dev,test]

# Set up pre-commit hooks (recommended)
pre-commit install
pre-commit run --all-files

# Run tests with coverage (30% minimum required for infrastructure)
pytest --cov=scripts --cov-report=term --cov-report=html

# Validate secrets references
python3 scripts/validate_secrets.py

# Validate Home Assistant configuration via Docker
docker run --rm -v "$PWD/config":/config ghcr.io/home-assistant/home-assistant:2024.11.3 \
  python -m homeassistant --script check_config --config /config

# Code quality checks (automated by pre-commit, but can run manually)
ruff check .                    # Linting
ruff format --check .           # Formatting
mypy config/custom_components   # Type checking
yamllint config/                # YAML linting
shellcheck scripts/*.sh         # Shell script linting
```

### Deployment
```bash
# PRIMARY: Automated deployment via GitHub Actions (recommended)
# - Push to main branch triggers CI validation
# - If CI passes, deploy-ssh-tailscale workflow deploys automatically
# - Includes health checks and notifications

git push origin main  # CI validates → tests → deploys → verifies

# MANUAL: Deploy via SSH/rsync (requires HA_HOST, HA_SSH_USER, HA_SSH_KEY env vars)
./scripts/deploy_via_ssh.sh

# SYNC UI CHANGES: Pull GUI-created automations/dashboards back to repo
./scripts/pull_gui_changes.sh

# ROLLBACK: Revert to previous deployment (see DISASTER_RECOVERY.md)
gh workflow run rollback.yml -f snapshot_run_id=<RUN_ID> -f confirm_rollback=ROLLBACK
```

## Architecture

### Custom Integration Structure

**IMPORTANT**: Custom components live in `config/custom_components/` (inside the config directory)

This repository includes:
- `config/custom_components/strava_coach/` — Strava Coach custom integration
  - Provides advanced training metrics (ATL, CTL, TSB, fitness/fatigue)
  - LLM-powered coaching insights
  - Integrates with ha-strava-coach subproject for data processing
- `ha-strava-coach/` — Separate Python package (subproject)
  - Advanced analytics engine
  - Independent testing and versioning
  - See `ha-strava-coach/README.md` for details

**Standard Home Assistant component pattern**:
1. `__init__.py` — Integration setup (`async_setup`, `async_setup_entry`)
2. `const.py` — Domain constants (`DOMAIN = 'strava_coach'`)
3. Platform files (`sensor.py`, `binary_sensor.py`) — Entity implementations
4. `config_flow.py` — UI-based configuration (OAuth flow)
5. `manifest.json` — Integration metadata and dependencies
6. `services.yaml` — Service definitions (if any)

### Configuration Layout
- `config/configuration.yaml` — Main HA config with package imports
- `config/packages/` — Modular feature configurations (packages pattern, see ADR 002)
  - `mqtt.yaml`, `strava_coach_dashboard.yaml`, `tuya.yaml`, etc.
  - Each package is self-contained with related sensors, automations, scripts
- `config/automations.yaml` — Automation definitions (can be UI-managed)
- `config/secrets.yaml` — Credentials (gitignored, use `secrets.yaml.example` as template)
- `config/custom_components/` — Custom integrations (strava_coach, etc.)
- `data/` — Inventory snapshots and HA mirror (see `data/README.md`)

**Packages Pattern** (see `docs/adr/002-packages-pattern.md`):
- Each package file is a complete HA configuration snippet merged at load time
- Enables feature-based organization, prevents merge conflicts
- Easy to disable features (rename to `.yaml.disabled`)

### Deployment Workflows

**Primary: Tailscale + SSH** (`.github/workflows/deploy-ssh-tailscale.yml`) — **Recommended**
- Connects via Tailscale VPN (no port forwarding, see ADR 001)
- Syncs config via rsync (excludes `.storage/`, database)
- Validates configuration before restart
- Performs health check (5-minute timeout)
- Creates deployment snapshots (artifacts, 90-day retention)
- Sends notifications (GitHub summary + optional Slack)

**Additional Workflows**:
- `ci.yml` — Validates config, runs tests, checks coverage, creates snapshots
- `rollback.yml` — Manual rollback to previous deployment (see DISASTER_RECOVERY.md)
- `inventory.yml` — Daily device/entity inventory snapshots (03:00 UTC)

## Coding Standards

### Python (Custom Integration)
- **Python 3.11+** required (root project), 3.12+ for ha-strava-coach subproject
- **Code style**: Enforced by Ruff (linting + formatting)
  - Line length: 100 characters
  - Follow PEP 8: 4-space indents, snake_case for modules/functions
  - Use type hints from `__future__ import annotations` (Home Assistant pattern)
- **Type checking**: MyPy strict mode enabled
- **Entity classes**: Inherit from `SensorEntity`, `BinarySensorEntity`, etc.
- **Attributes**: Use `_attr_*` class attributes for static properties when possible
- **Pre-commit**: Hooks run automatically before commits (ruff, mypy, trailing-whitespace, etc.)

### YAML Configuration
- **Indentation**: 2 spaces (enforced by yamllint)
- **Secrets**: Reference via `!secret key_name` (never commit actual secrets)
  - Validate with `python3 scripts/validate_secrets.py`
  - Template in `config/secrets.yaml.example`
- **Modularity**: Use `!include` and `!include_dir_named` (packages pattern)
- **Self-contained packages**: Each package file should be feature-complete

### Shell Scripts
- **Linting**: Shellcheck enforced in CI
- **SSH**: Use `StrictHostKeyChecking=accept-new` (not `no`)
- **Error handling**: Use `set -euo pipefail` at script start
- **Documentation**: Clear comments for complex operations

### Testing
- **Framework**: pytest with pytest-asyncio
- **Coverage**: **30% minimum required** (infrastructure), 70% target (see ADR 004)
  - Current: Infrastructure code (scripts, validation)
  - Future: Custom components unit tests
- **Structure**: All test files in `tests/` directory
  - `tests/conftest.py` — Shared fixtures and test data factories
  - `tests/test_config_validation.py` — Config structure and security tests
  - `tests/test_integrations.py` — Custom component validation
  - `tests/test_automations.py` — Automation validation and best practices
- **Async tests**: Use `pytest.mark.asyncio` decorator
- **CI validation**: Config validation (Docker) + pytest + coverage check

## Commit Conventions
Use Conventional Commits format:
- `feat: add new sensor platform`
- `fix: handle None state in sensor`
- `config: update automation trigger`
- `ci: update deployment workflow`

## Documentation

### Developer Resources
- **CONTRIBUTING.md** — Comprehensive developer onboarding guide
  - Development environment setup
  - Workflow (development, testing, commits, PRs)
  - Code quality standards and testing requirements
  - Troubleshooting common issues
- **DISASTER_RECOVERY.md** — Backup and restoration procedures
  - Three-layer backup strategy (Git, Artifacts, HA Backups)
  - Recovery scenarios with step-by-step instructions
  - Emergency procedures and rollback workflows
- **docs/adr/** — Architecture Decision Records
  - ADR 001: Tailscale for secure deployment
  - ADR 002: Packages pattern for modular configuration
  - ADR 003: Git-based configuration management (GitOps)
  - ADR 004: Test coverage requirements (phased approach: 30% → 70%)
- **data/README.md** — Inventory snapshots and HA mirror documentation
- **config/secrets.yaml.example** — Secret template with setup instructions

### Quick Links
- Testing guide: `CONTRIBUTING.md#testing`
- Deployment workflow: `CONTRIBUTING.md#deployment`
- Rollback procedure: `DISASTER_RECOVERY.md#scenario-1-rollback-recent-deployment`
- Secret validation: `scripts/validate_secrets.py`
- Inventory snapshots: `data/README.md#inventory-snapshots`

## Important Notes

### Security
- **Never commit**: `secrets.yaml`, `.storage/`, `home-assistant_v2.db*`, `*.db-*`
- **GitHub Secrets**: Store CI/CD credentials (TS_OAUTH_CLIENT_ID, HA_SSH_KEY, etc.)
  - See `config/secrets.yaml.example` for mapping to GitHub secrets
- **SSH Security**: Use `StrictHostKeyChecking=accept-new` (not `no`)
- **API Keys**: Rotate every 90 days, use read-only scopes when possible
- **Pre-commit hooks**: Detect secrets accidentally added to commits

### Configuration Changes
- **Always validate** before deployment:
  ```bash
  python3 scripts/validate_secrets.py  # Check secrets references
  docker run --rm -v "$PWD/config":/config \
    ghcr.io/home-assistant/home-assistant:2024.11.3 \
    python -m homeassistant --script check_config --config /config
  ```
- **Test changes**: Run `pytest --cov` before pushing (30% coverage required)
- **CI must pass**: Config validation + tests + coverage before merge
- **Sync UI changes**: Run `./scripts/pull_gui_changes.sh` before committing

### Custom Integration Development
- **Location**: `config/custom_components/strava_coach/` (inside config directory)
- **Subproject**: `ha-strava-coach/` is separate Python package with own tests
- **Adding platforms**: Create `sensor.py`, `binary_sensor.py`, etc.
- **Adding services**: Define in `services.yaml`, implement in `__init__.py`
- **Config flow**: Implement `config_flow.py` for UI-based setup (OAuth, etc.)
- **Testing**: Add tests to `tests/test_integrations.py`
- **Dependencies**: Update `manifest.json` and `pyproject.toml`
