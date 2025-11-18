# ADR 002: Modular Configuration with Packages Pattern

## Status

**Accepted** - November 2024

## Context

Home Assistant configuration can become complex and difficult to maintain as integrations grow. A monolithic `configuration.yaml` file becomes hard to navigate, prone to merge conflicts, and difficult for multiple contributors to work on.

### Alternatives Considered

1. **Monolithic configuration.yaml**
   - Pros: Single file, simple for small configs
   - Cons: Merge conflicts, hard to navigate, poor organization

2. **Split configs with !include**
   - Pros: Separation by platform (all sensors in one file)
   - Cons: Related configs scattered across files, poor modularity

3. **Packages pattern** ✅
   - Pros: Feature-based organization, self-contained modules, no merge conflicts
   - Cons: Slight learning curve

## Decision

We will use the **packages pattern** for organizing Home Assistant configuration, where each package is a self-contained YAML file representing a feature or integration.

### Implementation

```yaml
# config/configuration.yaml
homeassistant:
  packages: !include_dir_named packages

# config/packages/mqtt.yaml
mqtt:
  broker: !secret mqtt_broker
  port: !secret mqtt_port

sensor:
  - platform: mqtt
    name: "MQTT Example"
    state_topic: "home/sensor/test"

automation:
  - id: mqtt_device_offline
    alias: "MQTT: Device Offline Alert"
    trigger: ...
```

### Package Organization

Each package file contains:
- Integration configuration
- Related sensors/binary_sensors
- Associated automations
- Related scripts
- Relevant input_booleans/input_numbers

## Consequences

### Positive

✅ **Modularity**: Each integration is self-contained
✅ **Clarity**: Easy to find related configurations
✅ **Collaboration**: Multiple people can work on different packages
✅ **No Merge Conflicts**: Each package is independent
✅ **Reusability**: Packages can be shared between installations
✅ **Feature Flags**: Easy to disable entire integrations (rename .yaml.disabled)
✅ **Documentation**: Package files serve as feature documentation

### Negative

❌ **Learning Curve**: New pattern for HA beginners
❌ **Duplication**: Some configs might be repeated (e.g., logger settings)
❌ **Discovery**: Need to check multiple files for global settings

### Mitigations

- **Documentation**: CLAUDE.md explains pattern and rationale
- **Examples**: config/packages/ contains well-documented examples
- **Naming**: Clear, descriptive package names (mqtt.yaml, strava_coach_dashboard.yaml)
- **Comments**: Each package has header explaining purpose

## Package Guidelines

1. **One Integration Per Package**: Each package focuses on one integration/feature
2. **Self-Contained**: Include all related configs (sensors, automations, etc.)
3. **Well-Named**: Use descriptive names (not package1.yaml)
4. **Documented**: Header comment explaining package purpose
5. **Secrets**: Use !secret for sensitive data

## Examples

Current packages in this repository:
- `mqtt.yaml` - MQTT broker and related sensors
- `strava_coach_dashboard.yaml` - Strava Coach integration and dashboard
- `tuya.yaml` - Tuya smart home devices
- `xiaomi.yaml` - Xiaomi devices
- `solarman.yaml` - Solar inverter monitoring
- `onecta.yaml` - Daikin AC climate control

## Related

- See: config/packages/ for examples
- See: CLAUDE.md for coding standards
- Reference: [Home Assistant Packages Documentation](https://www.home-assistant.io/docs/configuration/packages/)
