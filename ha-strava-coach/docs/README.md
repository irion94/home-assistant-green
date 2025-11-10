## # Strava Coach for Home Assistant

![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)
![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.1+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

**Strava Coach** is a production-ready Home Assistant custom integration that analyzes your Strava training data to provide daily coaching suggestions based on fitness metrics (ATL/CTL/TSB) and readiness scoring.

## Features

- 🔐 **Secure OAuth2 Integration** with Strava
- 📊 **Advanced Fitness Metrics**: ATL (Fatigue), CTL (Fitness), TSB (Form), Readiness Score
- 🤖 **Optional AI Coaching**: GPT-4 powered suggestions (aggregates-only, privacy-first)
- 📅 **Daily Automated Sync**: Configurable sync time (default 07:00)
- 🔔 **Morning Notifications**: Push training suggestions to your mobile device
- 🛡️ **Privacy Compliant**: Strict data minimization, no Strava data used for AI training
- 📈 **Home Assistant Entities**: Sensors for readiness, fatigue, form, and daily suggestions
- ⚙️ **Services**: Manual sync and suggestion generation

## Quick Start

### Prerequisites

- Home Assistant 2024.1 or newer
- Strava API application (Client ID & Secret)
- (Optional) OpenAI API key for AI-powered suggestions

### Installation

#### Via HACS (Recommended)

1. Add this repository as a custom repository in HACS:
   - Go to HACS → Integrations → ⋮ → Custom repositories
   - URL: `https://github.com/yourusername/ha-strava-coach`
   - Category: Integration

2. Click "Install" and restart Home Assistant

#### Manual Installation

1. Download the latest release
2. Extract `strava_coach` folder to `/config/custom_components/`
3. Restart Home Assistant

### Configuration

1. **Set up Strava API Application**
   - See [STRAVA_SETUP.md](STRAVA_SETUP.md) for detailed instructions

2. **Add Integration**
   - Go to Settings → Devices & Services → Add Integration
   - Search for "Strava Coach"
   - Follow the OAuth2 flow to authorize Strava access
   - Configure:
     - Daily sync time (default 07:00)
     - History window (default 42 days)
     - (Optional) LLM settings

3. **Configure Automation**
   - Copy [example_automation.yaml](../example_automation.yaml) to your automations
   - Update `notify.mobile_app_YOUR_DEVICE` to your device

## Entities

### Sensors

| Entity ID | Description | Unit |
|-----------|-------------|------|
| `sensor.strava_coach_readiness` | Overall readiness score | % (0-100) |
| `sensor.strava_coach_fatigue` | Acute Training Load (7-day) | ATL |
| `sensor.strava_coach_form` | Training Stress Balance | TSB |
| `sensor.strava_coach_today_suggestion` | Daily training suggestion | Command |

### Sensor Attributes

**`sensor.strava_coach_readiness`**:
- `atl`: Acute Training Load
- `ctl`: Chronic Training Load
- `tsb`: Training Stress Balance
- `monotony`: Training variety index
- `window_days`: Historical analysis window

**`sensor.strava_coach_today_suggestion`**:
- `command`: Training command (e.g., `Z2_RIDE`, `REST_DAY`)
- `params`: Command parameters (duration, intervals, zone)
- `rationale_short`: Brief explanation

## Services

### `strava_coach.sync_now`

Manually trigger a sync with Strava.

```yaml
service: strava_coach.sync_now
```

### `strava_coach.generate_suggestion`

Generate a training suggestion for a specific date.

```yaml
service: strava_coach.generate_suggestion
data:
  date: "2025-01-15"  # Optional, defaults to today
  use_llm: false      # Optional, use LLM if enabled
```

## Training Commands

| Command | Description |
|---------|-------------|
| `REST_DAY` | Complete rest |
| `MOBILITY_20MIN` | Active recovery / mobility |
| `Z2_RIDE` | Aerobic endurance (Zone 2) |
| `TEMPO_RIDE` | Tempo training (Zone 3) |
| `SWEETSPOT_3x12` | Sweet spot intervals |
| `VO2MAX_5x3` | VO2max intervals |
| `ENDURO_TECH_SKILLS` | Technical skills practice |
| `STRENGTH_FULL_BODY` | Strength training |

## Privacy & Compliance

- **No AI Training**: Strava data is NOT used for AI model training (per Strava ToS)
- **Aggregates Only**: LLM mode uses only derived metrics (ATL/CTL/TSB), never raw activities
- **User-Only Display**: Data visible only to signed-in Home Assistant users
- **Opt-In LLM**: AI suggestions disabled by default, require explicit configuration

See [PRIVACY.md](PRIVACY.md) for details.

## Metrics Explained

### ATL (Acute Training Load)
7-day exponentially weighted moving average of training stress. Represents recent fatigue.

### CTL (Chronic Training Load)
42-day exponentially weighted moving average. Represents long-term fitness.

### TSB (Training Stress Balance)
`TSB = CTL - ATL`. Indicates form/freshness:
- **TSB < -20**: High fatigue, rest recommended
- **TSB -10 to +5**: Good training zone
- **TSB > +10**: Fresh, ready for intensity

### Readiness Score
Normalized 0-100 score combining TSB, training monotony, rest days, and load ratio.

## Troubleshooting

### No activities synced
- Check Strava OAuth authorization is valid
- Verify history window includes recent activities
- Check Home Assistant logs for API errors

### LLM suggestions not working
- Verify OpenAI API key is valid and has credits
- Check that LLM is enabled in configuration
- Review logs for API errors

### Entities showing "Unknown"
- Wait for initial sync to complete (triggered by coordinator)
- Manually trigger sync: `strava_coach.sync_now`

## Development

```bash
# Install development dependencies
make dev

# Run tests
make test

# Lint code
make lint

# Format code
make format
```

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass (`make test`)
5. Submit a pull request

## License

MIT License - see [LICENSE](../LICENSE) for details

## Acknowledgments

- Strava API for activity data
- Home Assistant community
- Training metrics based on TrainingPeaks methodology

## Support

- [Issues](https://github.com/yourusername/ha-strava-coach/issues)
- [Discussions](https://github.com/yourusername/ha-strava-coach/discussions)
- [Home Assistant Community](https://community.home-assistant.io/)
