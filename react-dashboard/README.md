# Home Assistant React Dashboard

A touch-optimized React dashboard for Home Assistant, designed for kiosk displays.

## Features

- **Real-time Updates**: WebSocket connection for instant state changes
- **Touch Optimized**: Large buttons, smooth sliders, swipe gestures
- **Dark Theme**: Easy on the eyes, perfect for wall-mounted displays
- **Voice Control**: Integrated with AI Gateway for natural language commands
- **Responsive**: Works on various screen sizes

## Pages

- **Overview**: Weather, quick actions, main sensors
- **Lights**: Control all lights with brightness sliders
- **Climate**: Temperature monitoring and heat pump control
- **Sensors**: Solar production, energy, all sensor readings
- **Voice**: Voice commands and text input for AI assistant

## Quick Start

### Development

```bash
# Install dependencies
npm install

# Create .env file with your HA token
cp .env.example .env
# Edit .env with your HA_TOKEN

# Start development server
npm run dev
```

Open http://localhost:3000

### Production (Docker)

The dashboard is included in the main docker-compose.yml:

```bash
cd ~/home-assistant-green/ai-gateway

# Build and start all services
docker-compose up -d --build react-dashboard

# View logs
docker-compose logs -f react-dashboard
```

Dashboard will be available at http://localhost:3000

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_HA_URL` | Home Assistant URL | `http://localhost:8123` |
| `VITE_HA_TOKEN` | Long-lived access token | (required) |
| `VITE_GATEWAY_URL` | AI Gateway URL | `http://localhost:8080` |

### Getting a Long-Lived Access Token

1. Go to your Home Assistant profile page
2. Scroll down to "Long-Lived Access Tokens"
3. Click "Create Token"
4. Copy the token and add it to your `.env` file

### Entity Configuration

Edit `src/config/entities.ts` to customize which entities appear on the dashboard:

```typescript
export const LIGHTS = {
  salon: {
    name: 'Living Room',
    entity_id: 'light.your_light_entity',
    icon: 'sofa',
  },
  // Add more lights...
}

export const SENSORS = {
  solarPower: 'sensor.your_solar_sensor',
  // Add more sensors...
}
```

## Kiosk Mode Setup

### Chromium Kiosk

```bash
chromium-browser \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --no-first-run \
  --start-fullscreen \
  http://localhost:3000
```

### Systemd Service

Create `/etc/systemd/system/dashboard-kiosk.service`:

```ini
[Unit]
Description=React Dashboard Kiosk
After=network.target docker.service

[Service]
Type=simple
User=your-user
Environment=DISPLAY=:0
ExecStart=/usr/bin/chromium-browser --kiosk http://localhost:3000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical.target
```

Enable and start:

```bash
sudo systemctl enable dashboard-kiosk
sudo systemctl start dashboard-kiosk
```

## Project Structure

```
react-dashboard/
├── src/
│   ├── api/           # HA REST & WebSocket clients
│   ├── components/    # UI components
│   │   ├── cards/     # LightCard, SensorCard, etc.
│   │   ├── common/    # Button, Slider, Toggle
│   │   └── layout/    # KioskLayout, Navigation
│   ├── hooks/         # React hooks for HA state
│   ├── pages/         # Main views
│   ├── config/        # Entity mappings
│   ├── types/         # TypeScript definitions
│   └── utils/         # Helpers and formatters
├── Dockerfile         # Production build
├── nginx.conf         # Nginx configuration
└── docker-compose.yml # (in parent ai-gateway/)
```

## Development

### Adding a New Entity Type

1. Add the entity ID to `src/config/entities.ts`
2. Create a card component in `src/components/cards/`
3. Add the card to the appropriate page

### Building for Production

```bash
npm run build
```

Output will be in `dist/` directory.

## Troubleshooting

### Connection Issues

- Verify HA token is correct and not expired
- Check that HA is accessible at the configured URL
- Look at browser console for WebSocket errors

### Entities Not Showing

- Verify entity IDs in `src/config/entities.ts`
- Check that entities exist in Home Assistant
- Ensure user has permission to access entities

### Docker Build Fails

```bash
# Clean rebuild
docker-compose build --no-cache react-dashboard

# Check logs
docker-compose logs react-dashboard
```

## License

MIT
