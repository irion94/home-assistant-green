# React Dashboard Architecture

## Overview

The React dashboard has been refactored (November 2025) to improve maintainability, performance, and extensibility through:
1. **Unified Zustand state management** replacing dual Context/Zustand patterns
2. **Atomic design component hierarchy** with shadcn/ui foundation
3. **Dynamic entity discovery** (planned - Phase 4)

## State Management Architecture

### Before: Dual State Systems

**Problem:** Two separate, non-integrated state management systems:

```
┌─────────────────────────────────────────────────────────┐
│ React Context (useHomeAssistant)                        │
│ - Entity states (Map<string, EntityState>)             │
│ - Connection status                                      │
│ - Service call methods                                   │
└─────────────────────────────────────────────────────────┘
       ↑ Callback pattern (causes re-render issues)

┌─────────────────────────────────────────────────────────┐
│ Zustand (voiceStore)                                    │
│ - Voice state (idle, listening, processing, speaking)   │
│ - Conversation messages                                  │
│ - MQTT integration                                       │
└─────────────────────────────────────────────────────────┘
```

**Issues:**
- Unclear boundaries between systems
- Context causes unnecessary re-renders
- Difficult to reason about data flow
- Voice state worked perfectly (direct Zustand writes from MQTT)
- Entity state had race conditions (callbacks)

### After: Unified Zustand Architecture

```
┌───────────────────────────────────────────────────────────────────┐
│ Zustand Stores (Single Source of Truth)                          │
├───────────────────────────────────────────────────────────────────┤
│ entityStore.ts                │ voiceStore.ts                     │
│ - Normalized entities         │ - Voice state machine             │
│ - Computed capabilities       │ - Conversation messages           │
│ - Service call actions        │ - MQTT integration                │
│ - Domain/room selectors       │ - Streaming state                 │
└───────────────────────────────────────────────────────────────────┘
                              ↑
                              │ Direct writes (no callbacks)
                              │
┌───────────────────────────────────────────────────────────────────┐
│ API Service Layer (services/api/)                                │
├───────────────────────────────────────────────────────────────────┤
│ HARestClient    │ HAWebSocket    │ MQTTService   │ GatewayClient │
│ - getStates()   │ - state_changed│ - Voice events│ - AI commands │
│ - callService() │ - Real-time    │ - Streaming   │ - Conversation│
└───────────────────────────────────────────────────────────────────┘
```

### Entity Store Details

**File:** `src/stores/entityStore.ts` (340 LOC)

**State Structure:**
```typescript
interface EntityStore {
  // Normalized state
  entities: Record<string, NormalizedEntity>
  loading: boolean
  connected: boolean
  error: string | null

  // Selectors (memoized in consumers)
  getEntity: (entityId: string) => NormalizedEntity | undefined
  getEntitiesByDomain: (domain: EntityDomain) => NormalizedEntity[]
  getLightEntities: () => NormalizedEntity[]

  // Actions
  setEntity: (entity: EntityState) => void
  setEntities: (entities: EntityState[]) => void
  updateEntityOptimistic: (entityId: string, updates: Partial<EntityState>) => void

  // Service calls (bound to API)
  toggle: (entityId: string) => Promise<void>
  turnOn: (entityId: string, data?: Record<string, unknown>) => Promise<void>
  setBrightness: (entityId: string, brightness: number) => Promise<void>
}
```

**Normalized Entity:**
```typescript
interface NormalizedEntity extends EntityState {
  // Computed once, cached
  isOn: boolean
  isAvailable: boolean
  domain: EntityDomain
  capabilities: EntityCapabilities
  displayName: string
  room?: string  // Future: from discovery service
}
```

**Capability Detection:**
- Lights: brightness, colorTemp, rgbColor (modern `supported_color_modes` + legacy `supported_features`)
- Climate: setTemperature, setHvacMode, setPresetMode
- Media: play, pause, volume
- Universal: turnOn, turnOff, toggle

**Benefits:**
- Capabilities computed once (not on every render)
- Optimistic updates for instant UI feedback
- Granular selectors prevent unnecessary re-renders
- Type-safe capability access

## API Layer Architecture

### Unified API Service

**File:** `src/services/api/index.ts` (180 LOC)

**Singleton Pattern:**
```typescript
class ApiService {
  public haRest: HomeAssistantClient
  public haWebSocket: HAWebSocket

  async initialize() {
    // 1. Fetch initial states via REST
    const states = await this.haRest.getStates()
    useEntityStore.getState().setEntities(states)

    // 2. Connect WebSocket
    await this.haWebSocket.connect()

    // 3. Subscribe to updates → write directly to store
    this.haWebSocket.onStateChange((entityId, newState) => {
      useEntityStore.getState().setEntity(newState)
    })

    // 4. Override store actions with real implementations
    this.connectStoreActions()
  }
}

export const api = new ApiService()
```

**Data Flow:**
```
Home Assistant
    ↓ REST API (initial fetch)
haClient.getStates()
    ↓
entityStore.setEntities()
    ↓
Components (useEntity hooks)

Home Assistant
    ↓ WebSocket (real-time updates)
haWebSocket.onStateChange()
    ↓
entityStore.setEntity()
    ↓
Components re-render (selective)
```

**Optimistic Updates:**
```typescript
toggle: async (entityId) => {
  // 1. Immediate UI update
  store.updateEntityOptimistic(entityId, {
    state: entity.isOn ? 'off' : 'on'
  })

  try {
    // 2. API call
    await haRest.toggle(entityId)
  } catch (error) {
    // 3. Revert on error
    const entity = await haRest.getState(entityId)
    store.setEntity(entity)
  }
}
```

## Component Architecture

### Atomic Design Hierarchy

**Atoms (shadcn/ui):**
- Button, Slider, Switch, Card, Dialog, Tabs
- Copy-paste components (you own the code)
- Tailwind CSS + Radix UI primitives
- Full accessibility built-in

**Molecules:**
- BrightnessControl: Slider + label + useBrightnessControl hook
- EntityCard: Icon + title + subtitle + children container
- Future: ColorPicker, MediaControls, VolumeControl

**Organisms:**
- Planned: LightControl (power + brightness + color + color temp)
- Planned: MediaPlayerControl (metadata + play/pause + volume)
- Planned: GenericEntityControl (universal renderer based on domain)

**Templates:**
- Planned: RoomDashboard (auto-generated room view)
- Planned: PanelTemplate (consistent panel structure)

**Pages:**
- KioskHome, Overview, Lights, Climate, Sensors, VoiceAssistant

### Gesture Hook Pattern

**Problem:** Duplicate gesture logic across components

**Solution:** Extract to reusable hooks

```typescript
// Before (duplicated in 3 components)
const [isDragging, setIsDragging] = useState(false)
const [localValue, setLocalValue] = useState(value)

useEffect(() => {
  if (!isDragging) setLocalValue(value)
}, [value, isDragging])

const handleChange = (newValue) => {
  setIsDragging(true)
  setLocalValue(newValue)
  onChange(newValue)
}

// After (single hook, reused)
const { localValue, isDragging, handleChange, handleChangeEnd } = useBrightnessControl({
  value,
  onChange,
  onChangeEnd,
})
```

**Available Gesture Hooks:**
- `useLongPress` - Long-press detection with threshold
- `useBrightnessControl` - Local state + optimistic updates
- `useColorPicker` - Color wheel drag interactions

## Design System

**File:** `src/design-system/tokens.ts` (220 LOC)

**Tokens:**
- Colors: Surface, semantic (success/warning/error), voice states, entity states
- Spacing: Touch targets (48px min), layout spacing, icon sizes
- Typography: Kiosk-optimized font sizes (readable from 2-3 feet)
- Animation: Duration + easing functions
- Z-index: Layering system

**Voice State Colors:**
```typescript
voiceState: {
  idle: '#6b7280',        // Gray
  listening: '#3b82f6',   // Blue
  processing: '#f59e0b',  // Orange
  speaking: '#22c55e',    // Green
  error: '#ef4444',       // Red
}
```

## Performance Optimizations

### 1. Granular Selectors

**Bad (causes re-renders on any entity change):**
```typescript
const allEntities = useEntityStore(state => state.entities)
const light = allEntities[entityId]
```

**Good (only re-renders when specific entity changes):**
```typescript
const light = useEntityStore(state => state.getEntity(entityId))
```

**Better (exported convenience hook):**
```typescript
const light = useEntity(entityId)  // Uses selector internally
```

### 2. Optimistic Updates

Immediate UI feedback without waiting for API round-trip:
```typescript
// Toggle appears instant (optimistic)
await entity.toggle()

// Brightness slider moves smoothly (local state)
<BrightnessControl value={localBrightness} onChange={setLocal} onChangeEnd={persistToApi} />
```

### 3. Capability Caching

Capabilities computed once on entity normalization:
```typescript
// Before (computed every render)
const supportsBrightness = useMemo(() => {
  return entity?.attributes.supported_color_modes?.includes('brightness') || Boolean(entity?.attributes.supported_features & 1)
}, [entity])

// After (cached in store)
const supportsBrightness = entity?.capabilities.brightness
```

## Migration Strategy

### Phase 1: Foundation ✅
- Install shadcn/ui
- Create atomic directory structure
- Design system tokens

### Phase 2: State Refactor ✅
- Create entityStore
- Consolidate API clients
- Migrate hooks
- Deprecate useHomeAssistant

### Phase 3: Component Extraction ✅
- Extract gesture hooks
- Create BrightnessControl molecule
- Create EntityCard molecule

### Phase 4: Dynamic Discovery (Planned)
- Entity discovery service
- Generic entity control
- Remove static entity config

### Phase 5: Missing Features (Planned)
- Color picker with presets
- Media player UI
- Scene/automation controls

### Phase 6: Polish (In Progress)
- Documentation
- Performance optimization
- Test coverage

## File Structure

```
src/
├── components/
│   ├── ui/              # shadcn/ui atoms (6 components)
│   ├── atoms/           # Custom atoms (future)
│   ├── molecules/       # BrightnessControl, EntityCard
│   ├── organisms/       # LightControl, EntityGrid (planned)
│   ├── templates/       # RoomDashboard (planned)
│   ├── layout/          # KioskLayout (existing)
│   ├── cards/           # Legacy cards (to be migrated)
│   ├── kiosk/           # Kiosk panels (to be refactored)
│   └── ApiProvider.tsx  # API initialization wrapper
├── design-system/
│   ├── tokens.ts        # Design system tokens
│   └── index.ts         # Barrel export
├── hooks/
│   ├── gestures/        # Gesture hooks (useLongPress, etc.)
│   ├── useEntity.ts     # Entity hooks (migrated to Zustand)
│   └── useHomeAssistant.tsx  # Deprecated (backward compat)
├── stores/
│   ├── entityStore.ts   # Entity state management
│   └── voiceStore.ts    # Voice state (unchanged)
├── services/
│   └── api/
│       ├── index.ts     # Unified API service
│       ├── ha-rest.ts   # Home Assistant REST client
│       └── ha-websocket.ts  # Home Assistant WebSocket client
├── types/
│   ├── entity.ts        # Entity type definitions
│   └── api.ts           # API type definitions
├── pages/               # Route components
└── App.tsx              # Root with ApiProvider
```

## Decision Log

### Why Zustand over Context?

**Reasons:**
1. Better performance (granular selectors)
2. No provider nesting hell
3. Simpler code (no useReducer boilerplate)
4. Better devtools (Redux DevTools)
5. voiceStore already used Zustand successfully

### Why shadcn/ui over Component Library?

**Reasons:**
1. You own the code (copy-paste, not npm install)
2. Full control over styling
3. Tailwind-based (matches existing approach)
4. Excellent accessibility (Radix UI)
5. No bundle size increase (tree-shakable)

**Alternatives Considered:**
- Mantine: Good but opinionated styling
- Chakra: Heavy, many abstractions
- Material-UI: Too opinionated, large bundle

### Why No Zod Validation?

**Decision:** TypeScript-only validation

**Reasons:**
1. User requirement (no runtime validation)
2. Lower overhead
3. Simpler codebase
4. Trust internal code

**Risk Mitigation:**
- MQTT messages from trusted backend
- WebSocket auth required
- Type guards for critical paths

## Future Enhancements

### Short-term (Phase 4-5)
- Dynamic entity discovery (remove static config)
- Media player UI implementation
- Color picker with kelvin/RGB controls
- Scene and automation panels

### Long-term (Post-Phase 6)
- Multi-room support (room filtering)
- Custom entity type registration (plugin pattern)
- Storybook for component documentation
- Visual regression tests
- Performance monitoring (React DevTools Profiler)

## References

- **Zustand:** https://docs.pmnd.rs/zustand
- **shadcn/ui:** https://ui.shadcn.com
- **Atomic Design:** https://bradfrost.com/blog/post/atomic-web-design/
- **Tailwind CSS:** https://tailwindcss.com
- **Home Assistant API:** https://developers.home-assistant.io/docs/api/rest
