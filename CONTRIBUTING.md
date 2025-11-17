# Contributing to Home Assistant Enterprise Starter

Thank you for your interest in contributing to this project! This guide will help you get started with development, testing, and deployment.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Environment Setup](#development-environment-setup)
- [Project Structure](#project-structure)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Quality](#code-quality)
- [Commit Conventions](#commit-conventions)
- [Pull Request Process](#pull-request-process)
- [Deployment](#deployment)
- [Getting Help](#getting-help)

## Getting Started

### Prerequisites

- **Git**: Version control
- **Python 3.11+**: For testing and local development
- **Docker**: For Home Assistant configuration validation
- **SSH Access** (optional): For deployment to Home Assistant
- **Tailscale** (optional): For secure deployment via VPN

### Fork and Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/home-assistant-green.git
cd home-assistant-green

# Add upstream remote
git remote add upstream https://github.com/irion94/home-assistant-green.git
```

## Development Environment Setup

### 1. Install Python Dependencies

```bash
# Install development dependencies
pip install -e .[dev,test]

# This installs:
# - pytest, pytest-asyncio, pytest-cov (testing)
# - ruff (linting and formatting)
# - mypy (type checking)
# - pre-commit (git hooks)
```

### 2. Set Up Pre-commit Hooks

```bash
# Install pre-commit hooks for code quality
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

### 3. Configure Secrets (Optional)

```bash
# Copy the secrets template
cp config/secrets.yaml.example config/secrets.yaml

# Edit with your actual credentials (gitignored)
# Only needed if you want to test with real integrations
```

### 4. Enable HA Sync Hook (Optional)

If you have SSH access to a Home Assistant instance:

```bash
# Install git hooks for HA sync
./scripts/install_git_hooks.sh

# Create .env.local with HA connection details
cat > .env.local << 'EOF'
HA_HOST=your-ha-host
HA_SSH_USER=root
HA_SSH_KEY=/path/to/ssh/key
HA_PREPUSH_MODE=gui  # Options: gui, components, full
EOF
```

## Project Structure

```
home-assistant-green/
├── .github/
│   ├── workflows/          # GitHub Actions CI/CD
│   │   ├── ci.yml          # Config validation, tests, linting
│   │   ├── deploy-ssh-tailscale.yml  # Production deployment
│   │   └── rollback.yml    # Rollback workflow
│   └── dependabot.yml      # Automated dependency updates
├── config/                 # Home Assistant configuration
│   ├── configuration.yaml  # Main HA config
│   ├── automations.yaml    # Automations (GUI-managed)
│   ├── packages/           # Modular config files
│   ├── blueprints/         # Automation blueprints
│   ├── dashboards/         # Lovelace dashboards
│   ├── themes/             # UI themes
│   └── custom_components/  # Custom integrations
├── scripts/                # Deployment and utility scripts
├── tests/                  # Test suite
├── docs/                   # Documentation
├── ha-strava-coach/        # Subproject for Strava Coach integration
├── pyproject.toml          # Python project configuration
├── .pre-commit-config.yaml # Pre-commit hooks configuration
└── CLAUDE.md               # AI assistant guidance
```

## Making Changes

### Branch Naming

Use descriptive branch names:

```bash
# Feature branches
git checkout -b feature/add-new-integration

# Bug fixes
git checkout -b fix/automation-trigger-issue

# Documentation
git checkout -b docs/update-contributing-guide

# Refactoring
git checkout -b refactor/simplify-deployment-script
```

### Configuration Changes

#### Adding Integrations

1. Add configuration to `config/packages/` (preferred) or `config/configuration.yaml`
2. Add required secrets to `config/secrets.yaml.example` with documentation
3. Update `.github/workflows/ci.yml` if new secrets are needed for validation
4. Test configuration validation:

```bash
# Validate configuration locally
docker run --rm \
  -v "$PWD/config":/config \
  ghcr.io/home-assistant/home-assistant:2024.11.3 \
  python -m homeassistant --script check_config --config /config
```

#### Modifying Automations

- Edit `config/automations.yaml` directly (or via HA UI)
- If editing via HA UI, sync changes back:

```bash
./scripts/pull_gui_changes.sh
git add config/automations.yaml
git commit -m "feat: add new automation for X"
```

### Custom Component Development

For custom integrations (like `strava_coach`):

1. Develop in `ha-strava-coach/` subproject (if applicable)
2. Copy to `config/custom_components/` for deployment
3. Follow Home Assistant component development guidelines
4. Add tests in `tests/` directory
5. Update manifest.json with proper version and dependencies

## Testing

### Run All Tests

```bash
# Run full test suite with coverage
pytest

# Run specific test file
pytest tests/test_config_validation.py

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov --cov-report=html
```

### Test Categories

**Configuration Validation Tests** (`test_config_validation.py`):
- YAML syntax validation
- Project structure checks
- Security validation (no hardcoded secrets)

**Integration Tests** (`test_integrations.py`):
- Custom component structure
- Manifest validation
- Deployment script validation

**Automation Tests** (`test_automations.py`):
- Automation schema validation
- Best practices checks
- Security scanning

### Validate Secrets

```bash
# Check that all !secret references have definitions
python scripts/validate_secrets.py --verbose
```

### Local Configuration Validation

```bash
# Using Docker (same as CI)
docker run --rm \
  -v "$PWD/config":/config \
  ghcr.io/home-assistant/home-assistant:2024.11.3 \
  python -m homeassistant --script check_config --config /config
```

## Code Quality

### Linting

```bash
# Run ruff linter
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .
```

### Type Checking

```bash
# Run mypy type checker
mypy config/custom_components tests/
```

### YAML Linting

```bash
# Install yamllint
pip install yamllint

# Lint YAML files
yamllint config/
```

### Shell Script Linting

```bash
# Install shellcheck
sudo apt-get install shellcheck  # or brew install shellcheck

# Lint shell scripts
shellcheck scripts/*.sh
```

### Pre-commit (Recommended)

Pre-commit runs all checks automatically:

```bash
# Install hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

## Commit Conventions

We use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, no logic change)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Maintenance tasks
- **ci**: CI/CD changes
- **config**: Home Assistant configuration changes

### Examples

```bash
# Feature
git commit -m "feat(automation): add motion-activated lighting"

# Bug fix
git commit -m "fix(sensor): correct temperature unit conversion"

# Configuration
git commit -m "config(mqtt): add Zigbee2MQTT integration"

# Documentation
git commit -m "docs: update deployment instructions"

# CI/CD
git commit -m "ci: add automated rollback workflow"
```

### Commit Message Guidelines

- Use present tense ("add feature" not "added feature")
- Use imperative mood ("move cursor to..." not "moves cursor to...")
- Limit first line to 72 characters
- Reference issues and PRs where applicable
- Provide detailed description in body for complex changes

## Pull Request Process

### 1. Ensure Quality

Before submitting a PR:

- [ ] All tests pass (`pytest`)
- [ ] Code is formatted (`ruff format .`)
- [ ] Linting passes (`ruff check .`)
- [ ] Type checking passes (`mypy`)
- [ ] Configuration validates (`docker run ...`)
- [ ] Pre-commit hooks pass (`pre-commit run --all-files`)
- [ ] Coverage remains above 70%

### 2. Update Documentation

- Update README.md if adding new features
- Add/update docstrings for new functions
- Update CHANGELOG.md if applicable
- Add comments for complex logic

### 3. Create Pull Request

```bash
# Push your branch
git push origin feature/your-feature-name

# Create PR on GitHub
# Fill in the PR template with:
# - Description of changes
# - Related issues
# - Testing performed
# - Screenshots (if UI changes)
```

### 4. PR Review Process

1. **Automated Checks**: CI runs tests, linting, validation
2. **Code Review**: Maintainers review code quality and design
3. **Testing**: Changes are tested in staging (if available)
4. **Approval**: At least one maintainer approval required
5. **Merge**: Squash and merge to master

### PR Title Format

Use conventional commits format:

```
feat(automation): add presence detection automation
fix(sensor): resolve temperature sensor timeout
docs: improve deployment documentation
```

## Deployment

### Local Deployment (Development)

```bash
# Deploy to your HA instance via SSH
HA_HOST=192.168.1.100 \
HA_SSH_USER=root \
HA_SSH_KEY=~/.ssh/ha \
./scripts/deploy_via_ssh.sh
```

### CI/CD Deployment (Production)

Deployment happens automatically:

1. **Push to master**: Triggers deployment workflow
2. **Validation**: CI validates configuration
3. **Drift Check**: Checks for GUI-managed changes
4. **Deploy**: Syncs config via SSH (Tailscale)
5. **Health Check**: Verifies HA comes back online
6. **Notification**: Reports success/failure

### Rollback

If deployment fails:

1. Navigate to **Actions** → **Rollback Deployment**
2. Enter the Run ID of a previous successful CI run
3. Type "ROLLBACK" to confirm
4. Workflow will restore previous configuration

## Testing Your Changes

### Test Locally Before PR

1. **Validate configuration**:
   ```bash
   python scripts/validate_secrets.py
   docker run --rm -v "$PWD/config":/config \
     ghcr.io/home-assistant/home-assistant:2024.11.3 \
     python -m homeassistant --script check_config --config /config
   ```

2. **Run tests**:
   ```bash
   pytest --cov
   ```

3. **Run linting**:
   ```bash
   ruff check .
   mypy config/custom_components tests/
   yamllint config/
   ```

4. **Test deployment** (if you have access):
   ```bash
   ./scripts/deploy_via_ssh.sh
   ```

### CI Testing

All PRs automatically run:
- Configuration validation
- Python tests with coverage
- YAML linting
- Shell script linting
- Security scanning (CodeQL)

## Code Style Guide

### Python

- **Style**: PEP 8 (enforced by ruff)
- **Line Length**: 100 characters
- **Type Hints**: Required (Python 3.11+)
- **Docstrings**: Google style
- **Imports**: Sorted with isort (via ruff)

Example:

```python
"""Module for handling sensor data."""

from __future__ import annotations

from typing import Any


def process_sensor_data(sensor_id: str, value: float) -> dict[str, Any]:
    """Process sensor data and return formatted result.

    Args:
        sensor_id: Unique identifier for the sensor
        value: Sensor reading value

    Returns:
        Dictionary containing processed sensor data

    Raises:
        ValueError: If sensor_id is empty or value is invalid
    """
    if not sensor_id:
        raise ValueError("sensor_id cannot be empty")

    return {
        "sensor_id": sensor_id,
        "value": value,
        "processed": True,
    }
```

### YAML

- **Indentation**: 2 spaces
- **Quotes**: Use for strings with special characters
- **Secrets**: Always use `!secret` for sensitive data
- **Comments**: Explain non-obvious configurations

Example:

```yaml
# MQTT sensor configuration
sensor:
  - platform: mqtt
    name: "Living Room Temperature"
    state_topic: "home/living_room/temperature"
    unit_of_measurement: "°C"
    device_class: temperature
    # Update every 30 seconds
    force_update: true
```

### Shell Scripts

- **Shebang**: `#!/usr/bin/env bash`
- **Error Handling**: `set -euo pipefail`
- **Comments**: Explain complex logic
- **Validation**: Use shellcheck

## Getting Help

### Resources

- **Documentation**: Check `docs/` directory
- **CLAUDE.md**: AI assistant guidance for the project
- **Issues**: Search existing issues on GitHub
- **Discussions**: Use GitHub Discussions for questions

### Asking Questions

When asking for help:

1. Search existing issues and discussions first
2. Provide context (what you're trying to achieve)
3. Include relevant code/configuration
4. Describe what you've tried
5. Include error messages and logs

### Reporting Bugs

Use the bug report template:

- **Description**: Clear description of the bug
- **Steps to Reproduce**: Detailed steps
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**: HA version, OS, etc.
- **Logs**: Relevant error logs

## Recognition

Contributors are recognized in:
- GitHub contributors page
- Release notes (for significant contributions)
- CHANGELOG.md

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

---

**Thank you for contributing!** 🎉

Your efforts help make this project better for everyone.
