# Phase 2: Configuration Abstraction

## Objective
Extract hardcoded entity configurations into a modular, typed structure that can be overridden per client.

## Current State
```typescript
// src/config/entities.ts - HARDCODED
export const LIGHTS = {
  salon: { name: 'Salon', entity_id: 'light.yeelight_color_0x80156a9', icon: 'sofa' },
  // ... more hardcoded entities
}
```

## Target State
```typescript
// src/config/types.ts - Shared types
export interface LightConfig {
  name: string;
  entity_id: string;
  icon: string;
}

export interface ClientConfig {
  lights: Record<string, LightConfig>;
  sensors: Record<string, SensorConfig>;
  climate: Record<string, ClimateConfig>;
  theme: ThemeConfig;
  features: FeatureFlags;
}

// src/config/defaults.ts - Base defaults (main branch)
export const DEFAULT_CONFIG: ClientConfig = {
  lights: {},
  sensors: {},
  climate: {},
  theme: { primaryColor: '#03a9f4', name: 'Default' },
  features: { voiceControl: true, climatePanel: false }
}

// src/config/entities.ts - Client override (client branch)
export const CLIENT_CONFIG: Partial<ClientConfig> = {
  lights: {
    salon: { name: 'Salon', entity_id: 'light.yeelight_color_0x80156a9', icon: 'sofa' },
  }
}
```

## Tasks

### 2.1 Create Type Definitions
```typescript
// src/config/types.ts
export interface LightConfig { ... }
export interface SensorConfig { ... }
export interface ClimateConfig { ... }
export interface ThemeConfig { ... }
export interface FeatureFlags { ... }
export interface ClientConfig { ... }
```

### 2.2 Create Default Configuration
```typescript
// src/config/defaults.ts
export const DEFAULT_CONFIG: ClientConfig = { ... }
```

### 2.3 Refactor Entity Files
- Split `entities.ts` into `lights.ts`, `sensors.ts`, `climate.ts`
- Create `index.ts` that merges defaults with client overrides

### 2.4 Update Component Imports
- Change all `import { LIGHTS } from '@/config/entities'`
- To `import { config } from '@/config'`

## Files Created/Modified
- `src/config/types.ts` (new)
- `src/config/defaults.ts` (new)
- `src/config/index.ts` (modified)
- `src/config/entities.ts` (modified - client overrides only)

## Validation
- [ ] TypeScript compiles without errors
- [ ] All components render with default config
- [ ] Client branch overrides work correctly
