# Phase 9: Docker Integration

## Objective
Update docker-compose.yml to work with external react-dashboard repository and pass client configuration.

## Updated docker-compose.yml

### react-dashboard service
```yaml
services:
  # ... other services ...

  react-dashboard:
    build:
      context: ../react-dashboard
      dockerfile: Dockerfile
      args:
        # Pass client config at build time
        - VITE_CLIENT_ID=${CLIENT_ID:-default}
        - VITE_CLIENT_NAME=${CLIENT_NAME:-Default}
        - VITE_HA_URL=http://localhost:8123
        - VITE_GATEWAY_URL=http://localhost:8080
        - VITE_MQTT_BROKER_URL=ws://localhost:9001
        - VITE_MQTT_TOPIC_VERSION=${MQTT_TOPIC_VERSION:-v1}
        - VITE_MQTT_BASE_PREFIX=${MQTT_BASE_PREFIX:-voice_assistant}
    container_name: react-dashboard
    ports:
      - "3000:3000"
    environment:
      # Runtime env (for nginx config, etc.)
      - CLIENT_ID=${CLIENT_ID:-default}
    depends_on:
      - ai-gateway
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Updated Dockerfile (react-dashboard)

```dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Accept build args
ARG VITE_CLIENT_ID=default
ARG VITE_CLIENT_NAME=Default
ARG VITE_HA_URL=http://localhost:8123
ARG VITE_GATEWAY_URL=http://localhost:8080
ARG VITE_MQTT_BROKER_URL=ws://localhost:9001
ARG VITE_MQTT_TOPIC_VERSION=v1
ARG VITE_MQTT_BASE_PREFIX=voice_assistant

# Set as env vars for Vite build
ENV VITE_CLIENT_ID=$VITE_CLIENT_ID
ENV VITE_CLIENT_NAME=$VITE_CLIENT_NAME
ENV VITE_HA_URL=$VITE_HA_URL
ENV VITE_GATEWAY_URL=$VITE_GATEWAY_URL
ENV VITE_MQTT_BROKER_URL=$VITE_MQTT_BROKER_URL
ENV VITE_MQTT_TOPIC_VERSION=$VITE_MQTT_TOPIC_VERSION
ENV VITE_MQTT_BASE_PREFIX=$VITE_MQTT_BASE_PREFIX

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Health check endpoint
RUN echo "OK" > /usr/share/nginx/html/health

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
```

## nginx.conf (react-dashboard)

```nginx
server {
    listen 3000;
    server_name localhost;
    root /usr/share/nginx/html;
    index index.html;

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "OK\n";
        add_header Content-Type text/plain;
    }

    # SPA routing - all routes to index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Don't cache HTML
    location ~* \.html$ {
        expires -1;
        add_header Cache-Control "no-store, no-cache, must-revalidate";
    }
}
```

## Build Context Verification

### .dockerignore (react-dashboard)
```
node_modules
dist
.git
.gitignore
*.md
.env*
.vscode
coverage
```

## Conditional Build (dev vs prod)

### docker-compose.override.yml (for local dev)
```yaml
# This file is auto-loaded with docker-compose.yml
services:
  react-dashboard:
    build:
      context: ../react-dashboard
      target: builder  # Use dev stage if defined
    volumes:
      # Mount source for hot reload (dev only)
      - ../react-dashboard/src:/app/src:ro
    command: npm run dev -- --host 0.0.0.0
```

## Multi-Client Deployment Example

### Client A deployment
```bash
# .env
CLIENT_ID=wojcik_igor
DASHBOARD_BRANCH=client/wojcik_igor
HA_SERVICE_BRANCH=client/wojcik_igor
```

### Client B deployment (different Raspberry Pi)
```bash
# .env
CLIENT_ID=kowalski_jan
DASHBOARD_BRANCH=client/kowalski_jan
HA_SERVICE_BRANCH=client/kowalski_jan
```

## Validation
- [ ] `docker compose build react-dashboard` succeeds
- [ ] Build args passed correctly (check with `docker inspect`)
- [ ] Dashboard accessible at http://localhost:3000
- [ ] Health check endpoint works
- [ ] Client ID visible in dashboard (footer/header)
