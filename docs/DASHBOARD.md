# Dashboard Configuration

This repository includes a modern dashboard example demonstrating best practices for Home Assistant Lovelace UI.

## Overview

The dashboard is configured in YAML mode and provides:
- **6 themed views**: Overview, Lights, Climate, System, Media, Settings
- **Modern card types**: Entity cards, button cards, gauges, sensor graphs, weather forecast
- **Responsive layouts**: Grid, horizontal-stack, vertical-stack
- **Real device integration**: Uses actual Aqara devices, system sensors, and automations from your inventory

## Files

- `config/packages/dashboard_example.yaml` — Dashboard configuration (registers the YAML dashboard)
- `config/dashboards/home.yaml` — Main dashboard layout with all views

## Dashboard Views

### 1. Overview
**Path:** `/lovelace/overview`

Main landing page featuring:
- Personalized welcome message with current date/time
- Weather forecast card
- Temperature and humidity graphs (24h)
- Quick action buttons for all lights
- Motion detection status (all 4 motion sensors + door sensor)
- System health gauges

### 2. Lights
**Path:** `/lovelace/lights`

Lighting control center:
- Grid of 18 Aqara single switch modules
- 8 Aqara LED strips with color/brightness control
- Group controls with toggle-all functionality
- Motion-activated lights automation toggle

### 3. Climate
**Path:** `/lovelace/climate`

Environmental monitoring and control:
- Weather forecast widget
- Indoor temperature graph (48h history)
- Indoor humidity graph (48h history)
- Climate automation controls (Daikin AC, TECH thermostat)

### 4. System
**Path:** `/lovelace/system`

System administration and monitoring:
- Home Assistant core updates (Core, Supervisor, OS)
- Add-on update status (Code Server, SSH, Tailscale, Mosquitto, Matter)
- Backup system status and schedule
- Network monitoring (router WAN status, speeds, external IP)
- Battery levels for all wireless sensors (9 devices)
- System automation management

### 5. Media
**Path:** `/lovelace/media`

Entertainment controls:
- TCL Smart TV media player card
- Radio Browser integration (placeholder for stations)

### 6. Settings
**Path:** `/lovelace/settings`

Configuration and tools:
- Network discovery scan trigger
- Shopping list access
- Person tracking (Igor)
- TTS service controls

## Usage

### Option 1: Use as Main Dashboard (YAML Mode)

The dashboard is already configured and will appear in the sidebar as "Smart Home" when you restart Home Assistant.

**To activate:**
1. The package is already included via `packages: !include_dir_named packages/` in `configuration.yaml`
2. Restart Home Assistant
3. Navigate to **Settings → Dashboards** and select "Smart Home"

**Note:** This disables UI dashboard editing. All changes must be made in YAML.

### Option 2: Keep as Secondary Dashboard

The current configuration adds it as a sidebar item alongside your default dashboard. No changes needed.

### Option 3: Disable YAML Dashboard

To revert to UI-configurable dashboards:
1. Comment out or delete `config/packages/dashboard_example.yaml`
2. Restart Home Assistant
3. Your original UI dashboard will be restored

## Customization

### Renaming Lights

The dashboard uses generic names (Switch 1, LED Strip 2, etc.). To add friendly names:

**Option A: Edit entity names in YAML**
```yaml
# config/customize.yaml
light.aqara_single_switch_module_t1:
  friendly_name: "Living Room Ceiling"
light.aqara_led_strip_t1:
  friendly_name: "Kitchen Counter"
```

**Option B: Update dashboard card names**
```yaml
# config/dashboards/home.yaml
- type: light
  entity: light.aqara_single_switch_module_t1
  name: Living Room Ceiling  # Override display name
```

### Adding Custom Cards

Popular custom card integrations (install via HACS):

- **[auto-entities](https://github.com/thomasloven/lovelace-auto-entities)** — Used for dynamic light grid
- **[card-mod](https://github.com/thomasloven/lovelace-card-mod)** — Custom CSS styling
- **[mini-graph-card](https://github.com/kalkih/mini-graph-card)** — Enhanced sensor graphs
- **[button-card](https://github.com/custom-cards/button-card)** — Highly customizable buttons
- **[mushroom-cards](https://github.com/piitaya/lovelace-mushroom)** — Modern minimalist cards

### Modifying Layouts

**Grid card - adjust columns:**
```yaml
- type: grid
  columns: 4  # Change to 2, 3, 5, etc.
  square: false  # Set to true for square tiles
```

**Conditional visibility:**
```yaml
- type: conditional
  conditions:
    - entity: person.igor
      state: home
  card:
    type: entities
    entities:
      - light.aqara_single_switch_module_t1
```

**Sensor graph customization:**
```yaml
- type: sensor
  entity: sensor.aqara_temp_humidity_sensor_temperature
  graph: line
  detail: 2  # 1 = less detail, 2 = more detail
  hours_to_show: 48  # Time range
```

## Card Types Reference

### Entity Card
Basic entity display with toggle/control:
```yaml
- type: entities
  title: My Devices
  state_color: true  # Color based on state
  show_header_toggle: true  # Toggle all
  entities:
    - entity: light.example
      name: Custom Name
      secondary_info: last-changed
```

### Light Card
Dedicated light control with brightness/color:
```yaml
- type: light
  entity: light.aqara_led_strip_t1
  name: LED Strip
```

### Sensor Card
Graph-enabled sensor display:
```yaml
- type: sensor
  entity: sensor.aqara_temp_humidity_sensor_temperature
  graph: line
  detail: 2
  hours_to_show: 24
```

### Button Card
Touch-optimized control button:
```yaml
- type: button
  entity: switch.example
  name: Toggle Switch
  tap_action:
    action: toggle
  icon: mdi:power
```

### Grid Card
Responsive grid layout:
```yaml
- type: grid
  columns: 3
  square: false
  cards:
    - type: button
      entity: light.example_1
    - type: button
      entity: light.example_2
```

### Gauge Card
Visual indicator with ranges:
```yaml
- type: gauge
  entity: sensor.battery_level
  name: Battery
  needle: true
  severity:
    green: 60
    yellow: 30
    red: 0
```

### Weather Forecast
Built-in weather card:
```yaml
- type: weather-forecast
  entity: weather.forecast_dom
  show_forecast: true
```

### Media Control
Media player interface:
```yaml
- type: media-control
  entity: media_player.smart_tv
```

### Markdown Card
Custom HTML/Markdown content:
```yaml
- type: markdown
  content: |
    # Welcome
    Current user: {{ states('person.igor') }}
    Time: {{ now().strftime('%H:%M') }}
```

## Templating

Home Assistant dashboards support Jinja2 templates in markdown cards:

**State values:**
```jinja2
{{ states('sensor.aqara_temp_humidity_sensor_temperature') }}°C
```

**Conditional text:**
```jinja2
{% if is_state('person.igor', 'home') %}
  Welcome home!
{% else %}
  House is empty
{% endif %}
```

**Calculations:**
```jinja2
Average: {{ (states('sensor.temp1') | float + states('sensor.temp2') | float) / 2 }}
```

## Troubleshooting

### Dashboard not appearing
- Check `config/packages/dashboard_example.yaml` is not commented out
- Verify `packages: !include_dir_named packages/` exists in `configuration.yaml`
- Restart Home Assistant completely (not just reload YAML)

### Entities not found
- Run inventory snapshot to verify entity IDs: `bash scripts/pull_inventory.sh && python3 scripts/build_inventory.py`
- Check `data/inventory/derived/entities.csv` for correct entity IDs
- Some entities may be disabled by default — enable in **Settings → Devices & Services**

### Cards showing "Entity not available"
- Verify device is online in **Settings → Devices & Services → Matter**
- Check Matter Server add-on is running
- Restart Matter Server if needed

### YAML errors on restart
- Validate YAML syntax: `docker run --rm -v "$PWD/config":/config ghcr.io/home-assistant/home-assistant:stable python -m homeassistant --script check_config --config /config`
- Common issues:
  - Incorrect indentation (use 2 spaces, not tabs)
  - Missing quotes around special characters
  - Invalid entity IDs

### Custom cards not working
- Install required custom integrations via HACS
- Clear browser cache after installing custom cards
- Check browser console for JavaScript errors (F12)

## Best Practices

### Performance
- Limit `hours_to_show` on sensor graphs (24-48h recommended)
- Use `detail: 1` for less critical graphs
- Avoid excessive auto-entities filters on slow devices

### Organization
- Group related entities logically (by room, function, or type)
- Use descriptive titles for cards
- Maintain consistent naming conventions

### Accessibility
- Use `state_color: true` for at-a-glance status
- Add `secondary_info: last-changed` for time-sensitive entities
- Include `icon:` for better visual recognition

### Maintenance
- Document custom entity names in comments
- Keep backup of working dashboard before major changes
- Test changes on a copy first (create new dashboard file)

## Resources

- [Official Lovelace Documentation](https://www.home-assistant.io/lovelace/)
- [Card Reference](https://www.home-assistant.io/dashboards/cards/)
- [HACS Custom Cards](https://hacs.xyz/docs/categories/plugin)
- [Community Dashboards](https://community.home-assistant.io/c/projects/dashboards/35)
- [Dashboard Templates](https://github.com/topics/home-assistant-dashboard)

## Examples

### Room-Specific View
```yaml
- title: Living Room
  path: living-room
  icon: mdi:sofa
  cards:
    - type: grid
      columns: 2
      cards:
        - type: light
          entity: light.living_room_ceiling
        - type: light
          entity: light.living_room_lamp

    - type: sensor
      entity: sensor.living_room_temperature
      graph: line
      hours_to_show: 24

    - type: entities
      title: Automations
      entities:
        - automation.living_room_motion_lights
        - automation.living_room_movie_mode
```

### Energy Monitoring (if sensors available)
```yaml
- title: Energy
  path: energy
  icon: mdi:lightning-bolt
  cards:
    - type: energy-distribution
      title: Energy Distribution

    - type: sensor
      entity: sensor.power_consumption
      graph: line
      hours_to_show: 24
      detail: 2

    - type: entities
      title: High Consumption Alerts
      entities:
        - automation.tauron_high_consumption_alert
        - automation.solarman_grid_export_detection
```

## Next Steps

1. **Customize entity names** — Update light/sensor names in dashboard or customize.yaml
2. **Add custom cards** — Install HACS and popular card integrations
3. **Create room views** — Organize devices by physical location
4. **Configure themes** — Add dark/light themes for better aesthetics
5. **Set up conditional cards** — Show/hide cards based on state or time
6. **Integrate custom icons** — Use MDI icons for better visual hierarchy
