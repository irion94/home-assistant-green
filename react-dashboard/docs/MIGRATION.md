# Migration Guide

## Overview

This guide helps you migrate components from the old Context-based pattern to the new Zustand entity store.

**TL;DR:**
- Replace `useHomeAssistant()` with `useEntity(entityId)` or domain-specific hooks
- Entity state is now in Zustand stores (not React Context)
- Service calls are now methods on entity objects
- Capabilities are pre-computed (no need for useMemo)

## Quick Migration

### Before: Context Pattern

```tsx
import { useHomeAssistant } from '@/hooks/useHomeAssistant'
import { isEntityOn } from '@/types/entity'

function LightCard({ entityId }) {
  const ha = useHomeAssistant()
  const entity = ha.getState(entityId)

  const isOn = entity ? isEntityOn(entity) : false
  const brightness = entity?.attributes.brightness
    ? Math.round((entity.attributes.brightness / 255) * 100)
    : 0

  const supportsBrightness = useMemo(() => {
    const modes = entity?.attributes.supported_color_modes
    return modes?.includes('brightness') || Boolean(entity?.attributes.supported_features & 1)
  }, [entity])

  const handleToggle = async () => {
    await ha.toggle(entityId)
  }

  const handleBrightness = async (value) => {
    await ha.setBrightness(entityId, Math.round(value * 2.55))
  }

  return (
    <div>
      <h3>{entity?.attributes.friendly_name}</h3>
      <button onClick={handleToggle}>{isOn ? 'On' : 'Off'}</button>
      {supportsBrightness && (
        <input type="range" value={brightness} onChange={(e) => handleBrightness(Number(e.target.value))} />
      )}
    </div>
  )
}
```

### After: Zustand Pattern

```tsx
import { useLightEntity } from '@/hooks/useEntity'
import { BrightnessControl, EntityCard } from '@/components/molecules'
import { Lightbulb } from 'lucide-react'

function LightCard({ entityId }) {
  const light = useLightEntity(entityId)

  return (
    <EntityCard
      icon={<Lightbulb />}
      title={light.entity?.displayName || entityId}
      subtitle={light.isOn ? 'On' : 'Off'}
      active={light.isOn}
      available={light.isAvailable}
      onClick={light.toggle}
      variant="normal"
    >
      {light.supportsBrightness && (
        <BrightnessControl
          value={light.brightness}
          onChange={(v) => {}}  // Optional: local state
          onChangeEnd={(v) => light.setBrightness(Math.round(v * 2.55))}
          variant="inline"
          showLabel
        />
      )}
    </EntityCard>
  )
}
```

**Benefits:**
- 60% less code
- No useMemo needed (capabilities cached)
- Reusable EntityCard and BrightnessControl
- Better performance (granular re-renders)

## Hook Migration

### useHomeAssistant → useEntity

| Old (Context) | New (Zustand) |
|---------------|---------------|
| `ha.getState(entityId)` | `useEntity(entityId)` |
| `ha.toggle(entityId)` | `entity.toggle()` |
| `ha.turnOn(entityId, data)` | `entity.turnOn(data)` |
| `ha.turnOff(entityId)` | `entity.turnOff()` |
| `ha.setBrightness(entityId, v)` | `entity.setBrightness(v)` |
| `ha.setTemperature(entityId, v)` | `entity.setTemperature(v)` |
| `ha.connected` | `useEntityStoreConnected()` |
| `ha.loading` | `useEntityStoreLoading()` |
| `ha.error` | `useEntityStoreError()` |

### Domain-Specific Hooks

**Lights:**
```tsx
// Old
const ha = useHomeAssistant()
const entity = ha.getState(entityId)
const brightness = entity?.attributes.brightness ? Math.round((entity.attributes.brightness / 255) * 100) : 0
const supportsBrightness = /* complex calculation */

// New
const light = useLightEntity(entityId)
// light.brightness (already converted to 0-100)
// light.supportsBrightness (already computed)
```

**Climate:**
```tsx
// Old
const ha = useHomeAssistant()
const entity = ha.getState(entityId)
const currentTemp = entity?.attributes.current_temperature ?? 0
const targetTemp = entity?.attributes.temperature ?? 0

// New
const climate = useClimateEntity(entityId)
// climate.currentTemperature
// climate.targetTemperature
// climate.hvacAction, climate.hvacModes, etc.
```

**Sensors:**
```tsx
// Old
const ha = useHomeAssistant()
const entity = ha.getState(entityId)
const value = entity?.state
const unit = entity?.attributes.unit_of_measurement

// New
const sensor = useSensorEntity(entityId)
// sensor.value, sensor.unit, sensor.deviceClass
```

### Getting Multiple Entities

**By Domain:**
```tsx
// Old
const ha = useHomeAssistant()
const allStates = Array.from(ha.states.values())
const lights = allStates.filter(e => e.entity_id.startsWith('light.'))

// New
const lights = useLightEntities()
// Returns NormalizedEntity[] with capabilities
```

**By Entity IDs:**
```tsx
// Old
const ha = useHomeAssistant()
const entities = entityIds.map(id => ha.getState(id))

// New
const entities = useEntities(entityIds)
```

## Component Migration

### Migrating Card Components

**Pattern: Replace Custom Card with EntityCard**

```tsx
// Before
<div className="card">
  <div className="flex items-center gap-3">
    <Lightbulb className={isOn ? 'text-primary' : 'text-gray-400'} />
    <div>
      <h3>{entity.attributes.friendly_name}</h3>
      <p>{isOn ? 'On' : 'Off'}</p>
    </div>
  </div>
  {/* controls */}
</div>

// After
<EntityCard
  icon={<Lightbulb />}
  title={entity.displayName}
  subtitle={isOn ? 'On' : 'Off'}
  active={isOn}
  available={entity.isAvailable}
>
  {/* controls */}
</EntityCard>
```

### Migrating Brightness Controls

**Pattern: Replace Custom Slider with BrightnessControl**

```tsx
// Before
const [localBrightness, setLocalBrightness] = useState(brightness)
const [isDragging, setIsDragging] = useState(false)

useEffect(() => {
  if (!isDragging) setLocalBrightness(brightness)
}, [brightness, isDragging])

<Slider
  value={[localBrightness]}
  onValueChange={(v) => {
    setIsDragging(true)
    setLocalBrightness(v[0])
  }}
  onValueCommit={(v) => {
    setIsDragging(false)
    entity.setBrightness(Math.round(v[0] * 2.55))
  }}
/>

// After
<BrightnessControl
  value={brightness}
  onChange={(v) => {}}  // Optional: for additional logic
  onChangeEnd={(v) => entity.setBrightness(Math.round(v * 2.55))}
  variant="inline"
  showLabel
/>
```

### Migrating Long-Press Gestures

**Pattern: Replace Custom Gesture Logic with useLongPress**

```tsx
// Before
const [pressTimer, setPressTimer] = useState<number | null>(null)
const [startPos, setStartPos] = useState<{ x: number, y: number } | null>(null)

const handlePointerDown = (e) => {
  setStartPos({ x: e.clientX, y: e.clientY })
  const timer = setTimeout(() => {
    onLongPress()
  }, 500)
  setPressTimer(timer)
}

const handlePointerUp = () => {
  if (pressTimer) clearTimeout(pressTimer)
  setPressTimer(null)
}

const handlePointerMove = (e) => {
  if (!startPos) return
  const distance = Math.sqrt(...)
  if (distance > 10 && pressTimer) {
    clearTimeout(pressTimer)
    setPressTimer(null)
  }
}

// After
const { handlers } = useLongPress({
  onLongPress: () => openFullControl(),
  threshold: 500,
  moveThreshold: 10,
})

<div {...handlers}>...</div>
```

## State Management Migration

### Provider Setup

**Old Setup (App.tsx):**
```tsx
<HomeAssistantProvider>
  <BrowserRouter>
    <Routes>...</Routes>
  </BrowserRouter>
</HomeAssistantProvider>
```

**New Setup (App.tsx):**
```tsx
<ApiProvider>
  <HomeAssistantProvider>  {/* Keep for backward compat during migration */}
    <BrowserRouter>
      <Routes>...</Routes>
    </BrowserRouter>
  </HomeAssistantProvider>
</ApiProvider>
```

**After Full Migration:**
```tsx
<ApiProvider>
  <BrowserRouter>
    <Routes>...</Routes>
  </BrowserRouter>
</ApiProvider>
```

## Deprecation Timeline

### Phase 1 (Current) - Coexistence
- Both Context and Zustand available
- useHomeAssistant emits console warnings
- New code should use Zustand hooks

### Phase 2 (Next) - Migration Period
- Gradually migrate components to Zustand
- Update tests to use new hooks
- Remove Context usage from components

### Phase 3 (Future) - Cleanup
- Remove HomeAssistantProvider
- Remove useHomeAssistant hook
- Remove Context-based code

## Common Patterns

### Pattern: Optimistic Toggle

```tsx
// Before (immediate update, but manual state management)
const [localIsOn, setLocalIsOn] = useState(isOn)
const handleToggle = async () => {
  setLocalIsOn(!localIsOn)
  try {
    await ha.toggle(entityId)
  } catch (error) {
    setLocalIsOn(localIsOn) // Revert
  }
}

// After (built-in optimistic updates)
const handleToggle = async () => {
  await entity.toggle()  // Optimistic update + revert on error handled internally
}
```

### Pattern: Entity Availability Check

```tsx
// Before
const isAvailable = entity?.state !== 'unavailable' && entity?.state !== 'unknown'

// After
const isAvailable = entity?.isAvailable  // Pre-computed
```

### Pattern: Capability Detection

```tsx
// Before (complex, error-prone)
const supportsBrightness = useMemo(() => {
  const modes = entity?.attributes.supported_color_modes as string[] | undefined
  if (modes?.length) {
    return modes.some(m => ['brightness', 'color_temp', 'hs', 'rgb'].includes(m))
  }
  const features = entity?.attributes.supported_features ?? 0
  return Boolean(features & 1)
}, [entity])

// After (simple, cached)
const supportsBrightness = entity?.capabilities.brightness
```

## Troubleshooting

### Console Warning: "useHomeAssistant is deprecated"

**Solution:** Migrate to `useEntity` or domain-specific hooks.

### Entity Not Found

**Problem:** `useEntity(entityId)` returns undefined

**Causes:**
1. Entity ID typo
2. Entity doesn't exist in Home Assistant
3. API not initialized yet

**Solution:**
```tsx
const entity = useEntity(entityId)
const loading = useEntityStoreLoading()
const error = useEntityStoreError()

if (loading) return <Spinner />
if (error) return <ErrorMessage error={error} />
if (!entity) return <div>Entity {entityId} not found</div>
```

### Service Call Fails Silently

**Problem:** Service call doesn't update entity

**Causes:**
1. Optimistic update succeeded, but API call failed
2. WebSocket not connected (update won't arrive)

**Solution:**
```tsx
const connected = useEntityStoreConnected()

if (!connected) return <div>Reconnecting...</div>

try {
  await entity.toggle()
} catch (error) {
  console.error('Toggle failed:', error)
  // Error will revert optimistic update automatically
}
```

### Performance Issues

**Problem:** Component re-renders too often

**Causes:**
1. Using entire store instead of selector
2. Using Map/Array from store without memoization

**Solution:**
```tsx
// Bad (re-renders on any entity change)
const allEntities = useEntityStore(state => state.entities)
const myEntity = allEntities[entityId]

// Good (only re-renders when this entity changes)
const myEntity = useEntity(entityId)

// Bad (re-renders on any light change)
const allLights = useEntityStore(state => state.getLightEntities())

// Good (memoized selector)
const lights = useLightEntities()
```

## Testing

### Before (Context Mocking)

```tsx
const mockHa = {
  getState: vi.fn(() => mockEntity),
  toggle: vi.fn(),
  // ...
}

<HomeAssistantContext.Provider value={mockHa}>
  <LightCard entityId="light.test" />
</HomeAssistantContext.Provider>
```

### After (Zustand Mocking)

```tsx
import { useEntityStore } from '@/stores/entityStore'

beforeEach(() => {
  useEntityStore.setState({
    entities: {
      'light.test': mockNormalizedEntity,
    },
  })
})

// No provider wrapping needed
render(<LightCard entityId="light.test" />)
```

## Checklist

- [ ] Replace `useHomeAssistant()` with `useEntity()` or domain hooks
- [ ] Replace custom cards with `EntityCard`
- [ ] Replace custom brightness sliders with `BrightnessControl`
- [ ] Replace custom gesture logic with gesture hooks
- [ ] Use pre-computed capabilities (no useMemo needed)
- [ ] Use domain-specific entity hooks (`useLightEntity`, etc.)
- [ ] Update tests to use Zustand mocking
- [ ] Remove Context provider wrapping (after migration complete)

## Support

- See `src/components/README.md` for component API documentation
- See `docs/ARCHITECTURE.md` for system architecture details
- Check existing migrated components for examples
- Ask questions in the team chat or create an issue
