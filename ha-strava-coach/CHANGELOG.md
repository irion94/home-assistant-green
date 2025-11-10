# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-01-09

### Added

#### Core Integration
- OAuth2 config flow for Strava authentication
- Automatic daily sync with configurable time (default 07:00)
- SQLite database for local activity and metrics storage
- DataUpdateCoordinator for scheduled updates

#### Metrics Engine
- Training load calculation (TRIMP-like) supporting:
  - Power-based (TSS-style) calculation
  - Heart rate-based (TRIMP) calculation
  - Fallback estimation using duration/distance/elevation
- ATL (Acute Training Load) - 7-day exponentially weighted moving average
- CTL (Chronic Training Load) - 42-day exponentially weighted moving average
- TSB (Training Stress Balance) - form/freshness indicator
- Readiness score (0-100) - multi-factor assessment
- Training monotony index

#### Sensors
- `sensor.strava_coach_readiness` - Overall readiness (0-100%)
- `sensor.strava_coach_fatigue` - ATL metric
- `sensor.strava_coach_form` - TSB metric
- `sensor.strava_coach_today_suggestion` - Daily coaching recommendation

#### Coaching System
- Rule-based suggestion engine with 8 training commands:
  - REST_DAY, MOBILITY_20MIN, Z2_RIDE, TEMPO_RIDE
  - SWEETSPOT_3x12, VO2MAX_5x3, ENDURO_TECH_SKILLS, STRENGTH_FULL_BODY
- Optional LLM integration (OpenAI GPT-4)
- Aggregates-only guardrails for LLM privacy compliance
- Context-aware suggestions based on readiness, form, and rest

#### Services
- `strava_coach.sync_now` - Manual Strava sync trigger
- `strava_coach.generate_suggestion` - Generate coaching suggestion for specific date

#### Privacy & Compliance
- Strict data minimization (Strava ToS compliant)
- Aggregates-only LLM mode (no raw Strava data transmitted)
- Runtime validation of LLM inputs with forbidden field detection
- Local-only data storage (SQLite)
- Opt-in LLM configuration (disabled by default)

#### Developer Experience
- Complete type hints (mypy strict mode)
- Ruff linting and formatting
- Pre-commit hooks
- Pytest test suite with >80% coverage
- GitHub Actions CI/CD
- Devcontainer support
- HACS-ready packaging

#### Documentation
- Comprehensive README with quickstart guide
- Privacy policy (PRIVACY.md)
- Strava API setup guide (STRAVA_SETUP.md)
- Home Assistant integration guide (HOME_ASSISTANT.md)
- LLM compliance documentation (LLM_COMPLIANCE.md)
- Example automation YAML
- Inline code documentation (Google-style docstrings)

### Security
- OAuth2 token refresh with automatic retry
- Rate limit tracking and backoff for Strava API
- Input validation for all config flow fields
- Secrets stored in Home Assistant config entry (encrypted)

---

## [Unreleased]

### Planned
- Webhook support for real-time activity sync (Nabu Casa / reverse proxy)
- HRV integration for enhanced readiness scoring
- Training plan templates
- Historical trend visualizations
- Multi-athlete support
- Additional LLM providers (Anthropic Claude)
- Integration with Home Assistant calendars
- Notification templates customization

---

**Legend**:
- `Added` - New features
- `Changed` - Changes in existing functionality
- `Deprecated` - Soon-to-be removed features
- `Removed` - Now removed features
- `Fixed` - Bug fixes
- `Security` - Security improvements
