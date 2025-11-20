# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a production Home Assistant deployment using GitOps workflow with:
- **Git-based configuration management** with automated CI/CD validation and deployment
- **Custom integrations**: Strava Coach (`config/custom_components/strava_coach/`)
- **AI Gateway**: FastAPI service bridging Ollama LLM ↔ Home Assistant for natural language control
- **Subproject**: Advanced Strava analytics (`ha-strava-coach/` - separate Python package)
- **Deployment**: Tailscale VPN + SSH/rsync for secure remote deployment
- **Testing**: 30% minimum test coverage (infrastructure), 70% target (full project)
- **Safe workflow**: validate → test → sync → deploy → health check → notify

## Build, Test, and Development Commands

### Local Development (Root Project)
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

### AI Gateway Development
```bash
# Navigate to AI Gateway
cd ai-gateway/

# Install AI Gateway dependencies
pip install -e .[dev,test]

# Run AI Gateway tests with coverage (30% minimum required)
pytest --cov=app --cov-report=term --cov-report=html --cov-fail-under=30

# Run AI Gateway locally (without Docker)
export HA_TOKEN=your_token
export HA_BASE_URL=http://localhost:8123
export OLLAMA_BASE_URL=http://localhost:11434
export OLLAMA_MODEL=llama3.2:3b
uvicorn app.main:app --reload --port 8080

# Build and start AI Gateway with Docker Compose
docker-compose up -d

# View AI Gateway logs
docker-compose logs -f ai-gateway

# Test AI Gateway endpoint
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"text": "Turn on living room lights"}'

# Check AI Gateway health
curl http://localhost:8080/health

# AI Gateway code quality
ruff check .                    # Linting
ruff format .                   # Formatting
mypy app/                       # Type checking
```

### Ollama Operations
```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# List installed models
ollama list

# Pull recommended model for RPi5 (2-3GB RAM, ~500ms-1s response)
ollama pull llama3.2:3b

# Test Ollama directly
ollama run llama3.2:3b "Turn on living room lights"

# For more powerful systems
ollama pull llama3.1:8b
ollama pull mistral:7b
```

### Deployment
```bash
# PRIMARY: Automated deployment via GitHub Actions (recommended)
# - Push to master branch triggers CI validation
# - If CI passes, deploy-ssh-tailscale workflow deploys automatically
# - Includes health checks and notifications

git push origin master  # CI validates → tests → deploys → verifies

# MANUAL: Deploy via SSH/rsync (requires HA_HOST, HA_SSH_USER, HA_SSH_KEY env vars)
./scripts/deploy_via_ssh.sh

# SYNC UI CHANGES: Pull GUI-created automations/dashboards back to repo
./scripts/pull_gui_changes.sh

# ROLLBACK: Revert to previous deployment (see DISASTER_RECOVERY.md)
gh workflow run rollback.yml -f snapshot_run_id=<RUN_ID> -f confirm_rollback=ROLLBACK
```

## Architecture

### AI Gateway Architecture

**Location**: `ai-gateway/` (FastAPI subproject)

The AI Gateway enables natural language control of Home Assistant:

```
User Command → AI Gateway → Ollama (LLM) → JSON Plan → Home Assistant → Action
     |              ↓
     |         API Endpoint (port 8080)
     |              ↓
     |         OllamaClient (LLM translation)
     |              ↓
     |         HAClient (HA service calls)
```

**Key Files**:
- `ai-gateway/app/main.py` — FastAPI application entry point
- `ai-gateway/app/routers/gateway.py` — `/ask` endpoint for NL processing
- `ai-gateway/app/services/ollama_client.py` — Ollama LLM integration with JSON validation
- `ai-gateway/app/services/ha_client.py` — Home Assistant REST API client
- `ai-gateway/docker-compose.yml` — HA + MQTT + AI Gateway orchestration
- `ai-gateway/pyproject.toml` — AI Gateway dependencies and configuration

**Service Dependencies**:
1. **Home Assistant** (container, port 8123) - Via `network_mode: host`
2. **MQTT Broker** (Mosquitto, ports 1883/9001) - For IoT devices
3. **AI Gateway** (container, port 8080) - Depends on HA health
4. **Ollama** (host, port 11434) - Accessed via `host.docker.internal`

**Persistent Storage** (SSD-backed):
- `/mnt/data-ssd/ha-data/ha-config` → Home Assistant configuration
- `/mnt/data-ssd/ha-data/mosquitto/{config,data,log}` → MQTT persistence
- Ollama models stored on host (avoid SD card)

### Custom Integration Structure

**IMPORTANT**: Custom components live in `config/custom_components/` (inside the config directory)

This repository includes:
- `config/custom_components/strava_coach/` — Strava Coach custom integration
  - Provides advanced training metrics (ATL, CTL, TSB, fitness/fatigue)
  - LLM-powered coaching insights
  - Integrates with ha-strava-coach subproject for data processing
- `config/custom_components/daikin_onecta/` — Daikin Onecta integration
- `config/custom_components/solarman/` — Solarman inverter integration
- `config/custom_components/xiaomi_home/` — Xiaomi Home integration
- `config/custom_components/tech/` — TECH Controllers integration
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
- `config/custom_components/` — Custom integrations (strava_coach, daikin_onecta, etc.)
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
- `deploy-webhook.yml` — Git Pull webhook deployment (alternative)
- `rollback.yml` — Manual rollback to previous deployment (see DISASTER_RECOVERY.md)
- `inventory.yml` — Daily device/entity inventory snapshots (03:00 UTC)
- `codeql.yml` — Security scanning

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

### AI Gateway Python Standards
- **Python 3.11+** required
- **FastAPI patterns**: Use dependency injection via `Depends()`
- **Async/await**: All I/O operations must be async (httpx for HTTP requests)
- **Pydantic models**: Use for request/response validation
- **Logging**: Structured JSON logging with correlation IDs
- **Error handling**: Graceful degradation, return meaningful errors
- **Type hints**: Required, enforced by MyPy strict mode

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
  - Current: Infrastructure code (scripts, validation) + AI Gateway
  - Future: Custom components unit tests
- **Structure**: All test files in `tests/` directory
  - `tests/conftest.py` — Shared fixtures and test data factories
  - `tests/test_config_validation.py` — Config structure and security tests
  - `tests/test_integrations.py` — Custom component validation
  - `tests/test_automations.py` — Automation validation and best practices
  - `ai-gateway/tests/` — AI Gateway-specific tests
- **Async tests**: Use `pytest.mark.asyncio` decorator
- **CI validation**: Config validation (Docker) + pytest + coverage check

## Commit Conventions
Use Conventional Commits format:
- `feat: add new sensor platform`
- `feat(ai-gateway): add entity mapping for bedroom`
- `fix: handle None state in sensor`
- `fix(ai-gateway): improve JSON validation`
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
- **INTEGRATIONS.md** — Integration setup guides
- **ai-gateway/README.md** — AI Gateway comprehensive documentation
  - Architecture and flow
  - API endpoints and examples
  - Deployment and configuration
  - Troubleshooting and performance optimization
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
- AI Gateway docs: `ai-gateway/README.md`

## Important Notes

### AI Gateway Considerations
- **Ollama models**: Use `llama3.2:3b` for Raspberry Pi 5 (2-3GB RAM, ~500ms-1s response)
- **Entity mapping**: Edit `ai-gateway/app/services/ollama_client.py` to add new entities
- **Bilingual support**: English and Polish commands supported out of the box
- **JSON validation**: All LLM output is validated before execution for safety
- **Performance**: First request ~2-3s (model load), subsequent ~500ms-1s
- **Health checks**: Use `/health` endpoint to verify Ollama and HA connectivity
- **Interactive docs**: Available at `http://localhost:8080/docs` (Swagger UI)

### Storage and Performance (Raspberry Pi 5)
- **SSD paths**: All persistent data on `/mnt/data-ssd/ha-data/`
  - HA config: `/mnt/data-ssd/ha-data/ha-config`
  - MQTT data: `/mnt/data-ssd/ha-data/mosquitto/`
  - Ollama models: Store on SSD (avoid SD card)
- **SD card**: Boot only, avoid write-heavy operations
- **Memory**: Monitor usage (Ollama can use 2-3GB, HA ~500MB-1GB)
- **Docker restart policies**: `unless-stopped` for all services

### Security
- **Never commit**: `secrets.yaml`, `.storage/`, `home-assistant_v2.db*`, `*.db-*`, `.env`
- **GitHub Secrets**: Store CI/CD credentials (TS_OAUTH_CLIENT_ID, HA_SSH_KEY, HA_TOKEN, etc.)
  - See `config/secrets.yaml.example` for mapping to GitHub secrets
  - See `ai-gateway/.env.example` for AI Gateway secrets
- **SSH Security**: Use `StrictHostKeyChecking=accept-new` (not `no`)
- **API Keys**: Rotate every 90 days, use read-only scopes when possible
- **HA Token**: Use long-lived access tokens (not admin passwords) for AI Gateway
- **Pre-commit hooks**: Detect secrets accidentally added to commits
- **Network security**: Run AI Gateway on trusted network or behind reverse proxy

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

### AI Gateway Development Workflow
1. **Make changes** to AI Gateway code (`ai-gateway/app/`)
2. **Add tests** for new functionality (`ai-gateway/tests/`)
3. **Run tests**: `cd ai-gateway && pytest --cov`
4. **Test locally**: `uvicorn app.main:app --reload`
5. **Test in Docker**: `docker-compose up --build`
6. **Verify coverage**: Must maintain 30%+ coverage
7. **Commit**: Follow conventional commits (`feat(ai-gateway): ...`)
8. **Deploy**: Push to master triggers CI/CD

### Troubleshooting AI Gateway
- **Ollama not reachable**: Check `OLLAMA_BASE_URL`, verify `host.docker.internal` works
- **HA not reachable**: Check `HA_BASE_URL`, verify token in `HA_TOKEN`
- **Invalid JSON from Ollama**: Check system prompt, try different model
- **Entity not found**: Verify entity ID exists in HA, check mapping in `ollama_client.py`
- **Slow responses**: First request loads model (~2-3s), subsequent faster
- **Container won't start**: Check logs with `docker-compose logs ai-gateway`
