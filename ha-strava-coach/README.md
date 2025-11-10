# Strava Coach for Home Assistant

[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/yourusername/ha-strava-coach/releases)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1+-green.svg)](https://www.home-assistant.io/)
[![License](https://img.shields.io/badge/license-MIT-orange.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

AI-powered fitness coaching for Home Assistant using your Strava training data. Get daily workout suggestions based on advanced metrics (ATL/CTL/TSB) and readiness scoring.

![Strava Coach Dashboard](https://via.placeholder.com/800x400.png?text=Strava+Coach+Dashboard+Screenshot)

## ✨ Features

- 🔐 Secure OAuth2 integration with Strava
- 📊 Advanced fitness metrics: ATL, CTL, TSB, Readiness (0-100)
- 🤖 Optional AI coaching with OpenAI GPT-4
- 📅 Automated daily sync and morning notifications
- 🛡️ Privacy-first: Aggregates-only LLM mode, Strava ToS compliant
- 📈 Home Assistant sensors and services
- 🔔 Mobile push notifications for daily suggestions

## 🚀 Quick Start

See [docs/README.md](docs/README.md) for complete documentation.

### Installation

1. Install via HACS or manually copy `custom_components/strava_coach` to your HA config
2. Add integration: Settings → Devices & Services → Add Integration → Strava Coach
3. Authorize Strava OAuth
4. Configure automation for morning notifications (see `example_automation.yaml`)

### Configuration

Required:
- Strava API application (Client ID & Secret) - [Setup Guide](docs/STRAVA_SETUP.md)

Optional:
- OpenAI API key for AI-powered suggestions
- Custom sync time (default 07:00 Europe/Warsaw)
- History window (default 42 days)

## 📊 Metrics

| Metric | Description | Range |
|--------|-------------|-------|
| **Readiness** | Multi-factor training readiness score | 0-100% |
| **ATL** | Acute Training Load (7-day fatigue) | 0-500 |
| **CTL** | Chronic Training Load (42-day fitness) | 0-500 |
| **TSB** | Training Stress Balance (form) | -50 to +50 |

## 🏋️ Training Commands

- `REST_DAY` - Complete rest
- `Z2_RIDE` - Aerobic endurance (Zone 2)
- `TEMPO_RIDE` - Tempo training (Zone 3)
- `SWEETSPOT_3x12` - Sweet spot intervals
- `VO2MAX_5x3` - VO2max intervals
- `STRENGTH_FULL_BODY` - Strength training
- `MOBILITY_20MIN` - Active recovery
- `ENDURO_TECH_SKILLS` - Technical skills

## 🔒 Privacy & Compliance

- ✅ Strava ToS compliant (no AI training on Strava data)
- ✅ Aggregates-only LLM mode (no raw activity data transmitted)
- ✅ Local SQLite storage (no cloud uploads)
- ✅ Opt-in LLM (disabled by default)

See [PRIVACY.md](docs/PRIVACY.md) for details.

## 🧪 Development

```bash
# Install dependencies
make dev

# Run tests
make test

# Lint & format
make lint
make format

# Run in devcontainer
code . # Open in VS Code with Dev Containers extension
```

## 📚 Documentation

- [Complete Documentation](docs/README.md)
- [Privacy Policy](docs/PRIVACY.md)
- [Strava Setup Guide](docs/STRAVA_SETUP.md)
- [Example Automation](example_automation.yaml)
- [Changelog](CHANGELOG.md)

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repo
2. Create a feature branch
3. Add tests
4. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details

## 🙏 Acknowledgments

- Strava API for activity data
- Home Assistant community
- TrainingPeaks methodology for fitness metrics

## 💬 Support

- [GitHub Issues](https://github.com/yourusername/ha-strava-coach/issues)
- [Home Assistant Community](https://community.home-assistant.io/)
