# Phase 5: API Config Endpoint

## Objective
Add an AI Gateway endpoint to serve client-specific dashboard configuration, enabling runtime config loading.

## Why API Endpoint?
- Allows config changes without rebuilding dashboard
- Centralized config management
- Can include dynamic data (entity discovery results)
- Fallback when static config not available

## API Design

### GET /api/dashboard/config
```json
{
  "client_id": "wojcik_igor",
  "client_name": "Igor Wójcik",
  "lights": {
    "salon": {
      "name": "Salon",
      "entity_id": "light.yeelight_color_0x80156a9",
      "icon": "sofa"
    }
  },
  "sensors": { ... },
  "climate": { ... },
  "theme": {
    "primaryColor": "#03a9f4",
    "logoUrl": "/assets/logo.svg"
  },
  "features": {
    "voiceControl": true,
    "climatePanel": true,
    "cameraPanel": false
  }
}
```

### Error Response
```json
{
  "error": "Config not found",
  "fallback": true,
  "config": { /* default config */ }
}
```

## Implementation

### ai-gateway/app/routers/dashboard.py
```python
from fastapi import APIRouter, Depends
from app.models import DashboardConfig
from app.services.config_loader import load_dashboard_config

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/config", response_model=DashboardConfig)
async def get_dashboard_config():
    """Return client-specific dashboard configuration."""
    config = await load_dashboard_config()
    return config
```

### ai-gateway/app/services/config_loader.py
```python
import json
from pathlib import Path
from app.models import DashboardConfig, ENV

CONFIG_PATH = Path("/app/config/dashboard.json")
DEFAULT_CONFIG_PATH = Path("/app/config/dashboard.default.json")

async def load_dashboard_config() -> DashboardConfig:
    """Load dashboard config from file or return defaults."""

    # Try client-specific config
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            return DashboardConfig(**json.load(f))

    # Fall back to defaults
    if DEFAULT_CONFIG_PATH.exists():
        with open(DEFAULT_CONFIG_PATH) as f:
            data = json.load(f)
            data["client_id"] = ENV.CLIENT_ID
            return DashboardConfig(**data)

    # Return minimal config
    return DashboardConfig(
        client_id=ENV.CLIENT_ID,
        client_name="Default",
        lights={},
        sensors={},
        climate={},
    )
```

### ai-gateway/app/models.py (additions)
```python
from pydantic import BaseModel
from typing import Dict, Optional

class EntityConfig(BaseModel):
    name: str
    entity_id: str
    icon: Optional[str] = None

class ThemeConfig(BaseModel):
    primaryColor: str = "#03a9f4"
    logoUrl: Optional[str] = None

class FeatureFlags(BaseModel):
    voiceControl: bool = True
    climatePanel: bool = False
    cameraPanel: bool = False

class DashboardConfig(BaseModel):
    client_id: str
    client_name: str
    lights: Dict[str, EntityConfig] = {}
    sensors: Dict[str, EntityConfig] = {}
    climate: Dict[str, EntityConfig] = {}
    theme: ThemeConfig = ThemeConfig()
    features: FeatureFlags = FeatureFlags()
```

## Config File Location

### docker-compose.yml mount
```yaml
ai-gateway:
  volumes:
    - ../home-assistant-service/dashboard:/app/config/dashboard:ro
```

### home-assistant-service/dashboard/config.json
```json
{
  "client_id": "wojcik_igor",
  "client_name": "Igor Wójcik",
  "lights": { ... }
}
```

## Validation
- [ ] `GET /api/dashboard/config` returns valid JSON
- [ ] Config loaded from mounted volume
- [ ] Fallback to defaults when file missing
- [ ] Swagger docs show endpoint
