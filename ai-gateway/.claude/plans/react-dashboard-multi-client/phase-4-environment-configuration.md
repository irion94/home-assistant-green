# Phase 4: Environment Configuration

## Objective
Add environment variables for client identification and configuration, integrated with Vite build system.

## Environment Variables

### ai-gateway/.env
```bash
# Existing
HA_SERVICE_BRANCH=client/wojcik_igor

# New
DASHBOARD_REPO=git@github.com:irion94/react-dashboard.git
DASHBOARD_BRANCH=client/wojcik_igor
CLIENT_ID=wojcik_igor
CLIENT_NAME="Igor Wójcik"
```

### react-dashboard/.env (local dev)
```bash
# Vite env vars must be prefixed with VITE_
VITE_CLIENT_ID=wojcik_igor
VITE_CLIENT_NAME="Igor Wójcik"
VITE_HA_URL=http://localhost:8123
VITE_GATEWAY_URL=http://localhost:8080
VITE_MQTT_BROKER_URL=ws://localhost:9001
```

### react-dashboard/.env.example
```bash
# Client Configuration
VITE_CLIENT_ID=default
VITE_CLIENT_NAME="Default Client"

# Home Assistant
VITE_HA_URL=http://localhost:8123

# AI Gateway
VITE_GATEWAY_URL=http://localhost:8080

# MQTT (WebSocket)
VITE_MQTT_BROKER_URL=ws://localhost:9001
VITE_MQTT_TOPIC_VERSION=v1
VITE_MQTT_BASE_PREFIX=voice_assistant
```

## Vite Configuration

### vite.config.ts
```typescript
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');

  return {
    plugins: [react()],
    define: {
      __CLIENT_ID__: JSON.stringify(env.VITE_CLIENT_ID || 'default'),
      __CLIENT_NAME__: JSON.stringify(env.VITE_CLIENT_NAME || 'Default'),
    },
  };
});
```

### src/config/env.ts
```typescript
export const ENV = {
  clientId: import.meta.env.VITE_CLIENT_ID || 'default',
  clientName: import.meta.env.VITE_CLIENT_NAME || 'Default Client',
  haUrl: import.meta.env.VITE_HA_URL || 'http://localhost:8123',
  gatewayUrl: import.meta.env.VITE_GATEWAY_URL || 'http://localhost:8080',
  mqttBrokerUrl: import.meta.env.VITE_MQTT_BROKER_URL || 'ws://localhost:9001',
} as const;
```

## Docker Environment Passing

### docker-compose.yml
```yaml
react-dashboard:
  build:
    context: ../react-dashboard
    args:
      - VITE_CLIENT_ID=${CLIENT_ID:-default}
      - VITE_CLIENT_NAME=${CLIENT_NAME:-Default}
      - VITE_HA_URL=${HA_BASE_URL:-http://localhost:8123}
      - VITE_GATEWAY_URL=http://localhost:8080
  environment:
    - VITE_CLIENT_ID=${CLIENT_ID:-default}
```

### Dockerfile (react-dashboard)
```dockerfile
ARG VITE_CLIENT_ID=default
ARG VITE_CLIENT_NAME=Default
ARG VITE_HA_URL=http://localhost:8123
ARG VITE_GATEWAY_URL=http://localhost:8080

ENV VITE_CLIENT_ID=$VITE_CLIENT_ID
ENV VITE_CLIENT_NAME=$VITE_CLIENT_NAME
# ... etc

RUN npm run build
```

## Validation
- [ ] `.env.example` exists with all variables documented
- [ ] Vite build picks up env vars correctly
- [ ] Docker build passes env vars as build args
- [ ] Runtime config shows correct client ID
