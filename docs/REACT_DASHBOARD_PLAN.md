# React Dashboard for Home Assistant - Implementation Plan

## Executive Summary

Build a touch-optimized React dashboard designed for wall-mounted kiosk displays. The dashboard connects to Home Assistant directly (for entity states and control) and the existing AI Gateway (for natural language commands and voice integration).

---

## Architecture

```
┌─────────────────────┐
│  React Dashboard    │
│  (Port 3000)        │
└─────────┬───────────┘
          │
    ┌─────┴─────┐
    │           │
    ▼           ▼
┌─────────┐ ┌─────────────┐
│ Home    │ │ AI Gateway  │
│Assistant│ │ (Port 8080) │
│ (8123)  │ └──────┬──────┘
└────┬────┘        │
     │             ▼
     │      ┌───────────┐
     │      │  Ollama   │
     │      │ (11434)   │
     │      └───────────┘
     ▼
┌─────────────┐
│   Devices   │
│ (lights,    │
│  sensors,   │
│  climate)   │
└─────────────┘
```

### Communication Flow

1. **Real-time updates**: React ↔ HA WebSocket API
2. **Device control**: React → HA REST API → Devices
3. **Voice/AI commands**: React → AI Gateway → Ollama → HA

---

## Project Structure

```
/home/irion94/home-assistant-green/
├── react-dashboard/                    # React application
│   ├── Dockerfile                      # Multi-stage build
│   ├── nginx.conf                      # Nginx for production serving
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── public/
│   │   └── manifest.json              # PWA manifest
│   └── src/
│       ├── main.tsx                   # App entry point
│       ├── App.tsx                    # Root component with router
│       ├── api/                       # API clients
│       │   ├── index.ts
│       │   ├── haClient.ts            # Home Assistant REST API
│       │   ├── haWebSocket.ts         # HA WebSocket for real-time
│       │   └── gatewayClient.ts       # AI Gateway API
│       ├── components/                # Reusable UI components
│       │   ├── cards/
│       │   │   ├── LightCard.tsx
│       │   │   ├── ClimateCard.tsx
│       │   │   ├── SensorCard.tsx
│       │   │   ├── MediaCard.tsx
│       │   │   └── WeatherCard.tsx
│       │   ├── common/
│       │   │   ├── Button.tsx
│       │   │   ├── Slider.tsx
│       │   │   ├── Toggle.tsx
│       │   │   └── Graph.tsx
│       │   └── layout/
│       │       ├── Header.tsx
│       │       ├── Navigation.tsx
│       │       └── KioskLayout.tsx
│       ├── hooks/                     # Custom React hooks
│       │   ├── useEntity.ts           # Single entity state
│       │   ├── useEntities.ts         # Multiple entities
│       │   ├── useWebSocket.ts        # Real-time updates
│       │   └── useVoiceCommand.ts     # Voice input
│       ├── pages/                     # Main views
│       │   ├── Overview.tsx           # Main dashboard
│       │   ├── Lights.tsx             # Light control
│       │   ├── Climate.tsx            # Temperature/climate
│       │   ├── Sensors.tsx            # All sensor data
│       │   └── VoiceAssistant.tsx     # AI voice interface
│       ├── config/                    # Configuration
│       │   └── entities.ts            # Entity mappings
│       ├── types/                     # TypeScript types
│       │   ├── entity.ts
│       │   └── api.ts
│       ├── utils/                     # Utilities
│       │   ├── entityHelpers.ts
│       │   └── formatters.ts
│       └── styles/                    # CSS/Tailwind
│           └── kiosk.css
└── docs/
    └── REACT_DASHBOARD_PLAN.md        # This file
```

---

## Implementation Phases

### Phase 1: Project Foundation

**Objective**: Set up React project with build tooling and Docker

**Tasks**:
1. Initialize React project with Vite + TypeScript
2. Configure Tailwind CSS for kiosk-optimized styling
3. Set up project structure and base files
4. Create Dockerfile (multi-stage build with nginx)
5. Create nginx.conf for SPA routing
6. Add service to docker-compose.yml

**Key Files**:
- `package.json` with dependencies
- `vite.config.ts` with build settings
- `tailwind.config.js` for dark theme
- `Dockerfile` and `nginx.conf`

---

### Phase 2: Home Assistant API Integration

**Objective**: Implement API clients for HA communication

**Tasks**:

1. **REST API Client** (`haClient.ts`):
   ```typescript
   export class HomeAssistantClient {
     private baseUrl: string;
     private token: string;

     async getStates(): Promise<EntityState[]>
     async getState(entityId: string): Promise<EntityState>
     async callService(domain: string, service: string, data: object): Promise<void>
     async getHistory(entityId: string, hours: number): Promise<HistoryData[]>
   }
   ```

2. **WebSocket Client** (`haWebSocket.ts`):
   ```typescript
   export class HAWebSocket {
     connect(): Promise<void>
     authenticate(token: string): Promise<void>
     subscribeToStateChanges(callback: (state: EntityState) => void): void
     disconnect(): void
   }
   ```

3. **React Hooks**:
   - `useEntity(entityId)` - Single entity state with toggle/control
   - `useEntities(domain)` - All entities of a domain
   - `useWebSocket()` - Connection management and state updates
   - `useHomeAssistant()` - Context provider for global state

---

### Phase 3: Core UI Components

**Objective**: Build touch-optimized, reusable components

**Components**:

1. **KioskLayout** - Full-screen layout with navigation
   - Dark background
   - Bottom navigation bar
   - Status indicators

2. **LightCard**
   - Room name and icon
   - On/off toggle (large touch target)
   - Brightness slider
   - Color temperature/color picker (if supported)

3. **ClimateCard**
   - Current temperature display (large font)
   - Target temperature controls (+/-)
   - Mode selector (heat/cool/auto)
   - Heat pump status indicator

4. **SensorCard**
   - Value with unit (large, readable)
   - Mini sparkline graph (24h)
   - Icon based on sensor type
   - Trend indicator (↑/↓)

5. **WeatherCard**
   - Current conditions icon
   - Temperature (current/feels like)
   - Humidity, wind
   - 3-day forecast

6. **Common Components**
   - `Button` - 48px minimum touch target
   - `Slider` - Large thumb, smooth animation
   - `Toggle` - Animated switch
   - `Graph` - Recharts-based time series

---

### Phase 4: Dashboard Pages

**Objective**: Create main view pages

1. **Overview Page** (`/`)
   - Weather widget (top)
   - Solar production summary
   - Quick light controls (main rooms)
   - Indoor/outdoor temperature
   - System status indicators

2. **Lights Page** (`/lights`)
   - Grid of room LightCards
   - "All Lights" master toggle
   - Brightness presets (25%, 50%, 75%, 100%)
   - Scene buttons

3. **Climate Page** (`/climate`)
   - Indoor temperature (large display)
   - Outdoor temperature
   - Heat pump control card
   - 24h temperature graph
   - Humidity readings

4. **Sensors Page** (`/sensors`)
   - Solar production (current + today's total)
   - Energy consumption
   - Battery level (if applicable)
   - All sensor readings in grid

---

### Phase 5: AI/Voice Integration

**Objective**: Connect to AI Gateway for voice commands

**Tasks**:

1. **Gateway Client** (`gatewayClient.ts`):
   ```typescript
   export class AIGatewayClient {
     async sendCommand(text: string): Promise<GatewayResponse>
     async conversation(text: string, sessionId: string): Promise<ConversationResponse>
     async voiceCommand(audio: Blob, sessionId: string): Promise<VoiceResponse>
   }
   ```

2. **VoiceAssistant Page** (`/voice`):
   - Large microphone button (center)
   - Visual feedback states:
     - Idle (gray)
     - Listening (blue pulse)
     - Processing (spinner)
     - Speaking (green)
   - Transcription display
   - AI response text
   - Conversation history

3. **useVoiceCommand Hook**:
   - Browser MediaRecorder API
   - Audio level visualization
   - Send to `/conversation/voice` endpoint
   - Handle streaming responses

---

### Phase 6: Polish and Optimization

**Objective**: Production-ready kiosk experience

**Tasks**:

1. **Touch Gestures**
   - Swipe left/right between pages
   - Pull down to refresh
   - Long press for options

2. **Screen Management**
   - Dim after 60s inactivity
   - Wake on touch
   - Prevent screen burn-in (subtle animation)

3. **Performance**
   - Lazy load pages
   - Memoize expensive renders
   - Optimize WebSocket reconnection
   - Cache entity states

4. **Error Handling**
   - Connection lost indicator
   - Retry logic with backoff
   - Graceful degradation

5. **PWA Configuration**
   - Service worker for offline
   - App manifest
   - Splash screen

---

## Technical Details

### Docker Configuration

**Dockerfile**:
```dockerfile
# Build stage
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;"]
```

**nginx.conf**:
```nginx
server {
    listen 3000;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://homeassistant:8123;
    }
}
```

**docker-compose.yml addition**:
```yaml
react-dashboard:
  build:
    context: ../react-dashboard
    dockerfile: Dockerfile
  container_name: react-dashboard
  ports:
    - "3000:3000"
  environment:
    - VITE_HA_URL=http://homeassistant:8123
    - VITE_HA_TOKEN=${HA_TOKEN}
    - VITE_GATEWAY_URL=http://ai-gateway:8080
  depends_on:
    - ai-gateway
    - homeassistant
  restart: unless-stopped
  networks:
    - ha-network
```

---

### Environment Variables

```env
# Home Assistant
VITE_HA_URL=http://homeassistant:8123
VITE_HA_TOKEN=your-long-lived-access-token

# AI Gateway
VITE_GATEWAY_URL=http://ai-gateway:8080

# Kiosk Settings
VITE_KIOSK_MODE=true
VITE_SCREEN_TIMEOUT=60000
VITE_LANGUAGE=pl
```

---

### Entity Mappings

Based on existing `ai-gateway/app/config/entities.py`:

```typescript
// src/config/entities.ts

export const LIGHTS = {
  salon: {
    name: 'Salon',
    entity_id: 'light.yeelight_color_0x80156a9',
    icon: 'sofa',
  },
  kuchnia: {
    name: 'Kuchnia',
    entity_id: 'light.yeelight_color_0x49c27e1',
    icon: 'utensils',
  },
  sypialnia: {
    name: 'Sypialnia',
    entity_id: 'light.yeelight_color_0x80147dd',
    icon: 'bed',
  },
  biurko: {
    name: 'Biurko',
    entity_id: 'light.yeelight_lamp15_0x1b37d19d_ambilight',
    icon: 'desktop',
  },
  korytarz: {
    name: 'Korytarz',
    entity_id: 'light.korytarz',
    icon: 'door-open',
  },
};

export const CLIMATE = {
  heatPump: {
    name: 'Pompa Ciepła',
    entity_id: 'climate.pompa_ciepla_room_temperature',
  },
};

export const SENSORS = {
  weather: 'weather.forecast_dom',
  solarPower: 'sensor.inverter_pv_power',
  solarToday: 'sensor.inverter_daily_production',
  batteryLevel: 'sensor.inverter_battery',
  indoorTemp: 'sensor.temperature_indoor',
  outdoorTemp: 'sensor.temperature_outdoor',
};

export const MEDIA = {
  nestHub: {
    name: 'Nest Hub',
    entity_id: 'media_player.nest_hub',
  },
};
```

---

### Kiosk-Specific Features

1. **Touch Targets**: Minimum 48x48px, 16px spacing
2. **Typography**: Large fonts (base 18px, headers 32px+)
3. **Colors**: Dark theme with high contrast accents
4. **Animations**: Smooth 200ms transitions
5. **No Scrollbars**: Fixed viewport layouts with pagination
6. **Wake/Sleep**: Touch to wake, auto-dim after timeout

---

### Key Dependencies

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "recharts": "^2.10.0",
    "@tanstack/react-query": "^5.8.0",
    "lucide-react": "^0.294.0",
    "framer-motion": "^10.16.0"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.2.0",
    "tailwindcss": "^3.3.0",
    "autoprefixer": "^10.4.0",
    "postcss": "^8.4.0"
  }
}
```

---

### Home Assistant API Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/states` | GET | All entity states |
| `/api/states/{entity_id}` | GET | Single entity state |
| `/api/services/{domain}/{service}` | POST | Call a service |
| `/api/history/period/{timestamp}` | GET | Historical data |
| `/api/websocket` | WS | Real-time state updates |

**WebSocket Message Types**:
- `auth` - Authentication
- `subscribe_events` - Subscribe to state changes
- `call_service` - Execute service
- `get_states` - Fetch all states

---

## Kiosk Deployment

### Chromium Kiosk Mode

```bash
chromium-browser \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --no-first-run \
  --enable-features=OverlayScrollbar \
  --start-fullscreen \
  http://localhost:3000
```

### Systemd Service

```ini
[Unit]
Description=React Dashboard Kiosk
After=network.target docker.service

[Service]
Type=simple
User=irion94
Environment=DISPLAY=:0
ExecStart=/usr/bin/chromium-browser --kiosk http://localhost:3000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=graphical.target
```

---

## Troubleshooting

### Common Issues

1. **WebSocket connection fails**
   - Check HA token is valid
   - Verify network connectivity
   - Check CORS settings

2. **Entities not updating**
   - Verify WebSocket subscription
   - Check entity_id spelling
   - Review HA logs

3. **Slow performance on RPi**
   - Enable hardware acceleration
   - Reduce animation complexity
   - Optimize re-renders with memo

4. **Touch not responding**
   - Check touch driver (libinput)
   - Calibrate touchscreen
   - Verify kiosk mode settings

---

## Execution Instruction

**Proceed with all phases until you finish the working dashboard.**

Start with Phase 1 (Project Foundation) and continue through Phase 6 (Polish and Optimization). Create all necessary files, configure Docker, implement API clients, build UI components, and ensure the dashboard is fully functional and deployable.
