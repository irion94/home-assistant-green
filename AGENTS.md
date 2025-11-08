# Repository Guidelines

## Project Structure & Module Organization
- `config/` Home Assistant configuration. Key paths:
  - `config/custom_components/enterprise_example/` custom integration (Python).
  - `config/packages/` feature-scoped YAML.
  - `configuration.yaml`, `automations.yaml`, `secrets.yaml.example`.
- `scripts/` deployment helpers (`deploy_via_ssh.sh`, `deploy_via_webhook.sh`).
- `tests/` pytest suite for the custom integration.
- `.github/workflows/` CI (config validation + tests) and deploy workflows.

## Build, Test, and Development Commands
- Install test deps: `pip install -e .[test]`
- Run tests: `pytest -q`
- Check HA config via Docker:
  ```bash
  docker run --rm -v "$PWD/config":/config ghcr.io/home-assistant/home-assistant:stable \
    python -m homeassistant --script check_config --config /config
  ```
- Deploy via webhook (CI uses this): `WEBHOOK_URL=... ./scripts/deploy_via_webhook.sh`
- Deploy via SSH/rsync (requires HA SSH add-on): set `HA_HOST`, `HA_SSH_USER`, `HA_SSH_KEY` then run `./scripts/deploy_via_ssh.sh`.

## Coding Style & Naming Conventions
- Python 3.11+. Follow PEP 8, 4‑space indents, type hints where practical.
- Modules and files: `snake_case`; constants in `const.py` (e.g., `DOMAIN`).
- Home Assistant entities/components mirror core patterns (e.g., `SensorEntity`).
- YAML: two‑space indents; anchor secrets via `secrets.yaml` (never commit real secrets).

## Testing Guidelines
- Framework: `pytest` (+ `pytest-asyncio`). Async tests use `pytest.mark.asyncio`.
- Location: place tests under `tests/`; name files `test_*.py`.
- Aim to cover integration setup (`async_setup`, entities) and config parsing. Run `pytest -q` locally and in CI.

## Commit & Pull Request Guidelines
- Commits: use Conventional Commits (e.g., `feat: add hello sensor`, `fix: handle None state`).
- PRs: include clear description, linked issues, and scope (config vs. integration). Add screenshots/log snippets when helpful. Keep changes minimal and focused.
- CI must pass (config validation + tests). For config-only PRs, note any required secrets.

## Security & Configuration Tips
- Do not commit `.storage/` or `home-assistant_v2.db*`. Use `secrets.yaml` locally and environment/GitHub Secrets in CI.
- Review `.github/workflows/*` before enabling deploy to ensure target host/URL is correct.

