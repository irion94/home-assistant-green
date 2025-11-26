# Component Library Guide

## Overview

The React dashboard uses **Atomic Design** principles for component organization. Components are organized into five levels: atoms, molecules, organisms, templates, and pages.

## Component Hierarchy

```
components/
├── ui/              # Atoms (shadcn/ui primitives)
├── atoms/           # Custom atoms
├── molecules/       # Composite components (2-3 atoms)
├── organisms/       # Feature-complete sections
├── templates/       # Page layouts
└── pages/           # Routes (outside components/)
```

## shadcn/ui Components (Atoms)

Located in `components/ui/`, these are copy-paste components from [shadcn/ui](https://ui.shadcn.com/).

**Available Components:**
- `Button` - Interactive button with variants
- `Slider` - Range input for numeric values
- `Switch` - Toggle switch
- `Card` - Content container with header/footer
- `Dialog` - Modal dialog overlay
- `Tabs` - Tabbed interface

**Usage:**
```tsx
import { Button, Slider, Card } from '@/components/ui'

<Button variant="primary">Click me</Button>
<Slider value={[50]} onValueChange={(v) => console.log(v)} />
<Card>
  <CardHeader>
    <CardTitle>Entity Name</CardTitle>
  </CardHeader>
  <CardContent>Content here</CardContent>
</Card>
```

## Molecules

Composite components combining 2-3 atoms. Reusable across different contexts.

### BrightnessControl

Brightness slider with local state management.

**Props:**
- `value`: number (0-100)
- `onChange`: (value: number) => void
- `onChangeEnd?`: (value: number) => void
- `variant`: 'inline' | 'modal'
- `showLabel?`: boolean

**Usage:**
```tsx
import { BrightnessControl } from '@/components/molecules'

<BrightnessControl
  value={entity.brightness}
  onChange={(v) => setLocalBrightness(v)}
  onChangeEnd={(v) => entity.setBrightness(Math.round(v * 2.55))}
  variant="inline"
  showLabel
/>
```

### EntityCard

Generic card wrapper for entity displays.

**Props:**
- `icon`: ReactNode - Icon element
- `title`: string - Primary text
- `subtitle?`: string - Secondary text
- `active?`: boolean - Active state (on/playing)
- `available?`: boolean - Entity availability
- `onClick?`: () => void - Click handler
- `variant`: 'compact' | 'normal' | 'large'
- `children?`: ReactNode - Control elements

**Usage:**
```tsx
import { EntityCard } from '@/components/molecules'
import { Lightbulb } from 'lucide-react'

<EntityCard
  icon={<Lightbulb />}
  title="Living Room"
  subtitle={entity.isOn ? 'On' : 'Off'}
  active={entity.isOn}
  available={entity.isAvailable}
  onClick={() => entity.toggle()}
  variant="normal"
>
  <BrightnessControl value={entity.brightness} onChange={setBrightness} />
</EntityCard>
```

## Organisms

Feature-complete sections combining multiple molecules.

### Planned Organisms

- **LightControl** - Full light control (power, brightness, color, color temp)
- **MediaPlayerControl** - Media player UI (play/pause, volume, metadata)
- **ClimateControl** - Thermostat controls (temp, mode, presets)
- **GenericEntityControl** - Universal entity renderer (Phase 4)
- **EntityGrid** - Grid layout for entity tiles (Phase 4)

## Gesture Hooks

Reusable hooks for touch/mouse interactions.

### useLongPress

Detects long-press gestures.

```tsx
import { useLongPress } from '@/hooks/gestures'

const { handlers, isPressing } = useLongPress({
  onLongPress: () => console.log('Long pressed!'),
  onPress: () => console.log('Short press'),
  threshold: 500,
  moveThreshold: 10,
})

<button {...handlers}>Press and hold</button>
```

### useBrightnessControl

Manages local brightness state during drag.

```tsx
import { useBrightnessControl } from '@/hooks/gestures'

const { localValue, isDragging, handleChange, handleChangeEnd } = useBrightnessControl({
  value: entity.brightness,
  onChange: (v) => setLocal(v),
  onChangeEnd: (v) => entity.setBrightness(v),
})

<Slider value={[localValue]} onValueChange={handleChange} onValueCommit={handleChangeEnd} />
```

### useColorPicker

Handles color wheel drag interactions.

```tsx
import { useColorPicker } from '@/hooks/gestures'

const { handlers, isDragging, indicatorPosition } = useColorPicker({
  value: { hue: 180, saturation: 50 },
  onChange: (color) => setLocal(color),
  onChangeEnd: (color) => entity.setColor(color),
  size: 200,
})

<div {...handlers} style={{ width: 200, height: 200 }}>
  <div style={{ transform: `translate(${indicatorPosition.x}px, ${indicatorPosition.y}px)` }} />
</div>
```

## Design Tokens

Centralized design system in `src/design-system/tokens.ts`.

**Available Tokens:**
- `colors` - Surface, semantic, voice state, entity state colors
- `spacing` - Touch targets, layout spacing, icon sizes
- `typography` - Font sizes, weights, line heights
- `borderRadius` - Consistent corner rounding
- `animation` - Duration and easing functions
- `zIndex` - Layering system

**Usage:**
```tsx
import { colors, spacing } from '@/design-system'

<div style={{
  backgroundColor: colors.surface,
  padding: spacing.cardPadding,
  borderRadius: borderRadius.md,
}}>
```

## State Management

### Entity Store (Zustand)

Centralized entity state management.

**Hooks:**
- `useEntity(entityId)` - Single entity
- `useLightEntity(entityId)` - Light with capabilities
- `useClimateEntity(entityId)` - Climate controls
- `useSensorEntity(entityId)` - Sensor data
- `useLightEntities()` - All lights
- `useEntityStoreConnected()` - Connection state

**Usage:**
```tsx
import { useLightEntity } from '@/hooks/useEntity'

function LightCard({ entityId }) {
  const light = useLightEntity(entityId)

  return (
    <EntityCard
      title={light.entity?.displayName}
      active={light.isOn}
      onClick={light.toggle}
    >
      {light.supportsBrightness && (
        <BrightnessControl value={light.brightness} onChange={light.setBrightness} />
      )}
    </EntityCard>
  )
}
```

### Voice Store (Zustand)

Separate store for voice assistant state (unchanged from before).

**Usage:**
```tsx
import { useVoiceStore } from '@/stores/voiceStore'

const { state, messages, conversationMode } = useVoiceStore()
```

## Adding New Components

### Adding a New Molecule

1. Create component file in `src/components/molecules/YourComponent.tsx`
2. Export from `src/components/molecules/index.ts`
3. Write JSDoc documentation
4. Use shadcn/ui atoms where possible
5. Use design tokens for styling

### Adding a New Organism

1. Create component file in `src/components/organisms/YourComponent.tsx`
2. Compose from molecules and atoms
3. Export from `src/components/organisms/index.ts`
4. Keep under 200 LOC (split if larger)

## Best Practices

1. **Prefer Composition over Props**
   - Use `children` for flexible content
   - Avoid boolean props for variants (use union types)

2. **Use Design Tokens**
   - Import from `@/design-system`
   - Avoid magic numbers

3. **TypeScript Props**
   - Export prop interfaces
   - Use discriminated unions for variants
   - Document with JSDoc

4. **Performance**
   - Use Zustand selectors for granular updates
   - Memoize expensive calculations
   - Lazy load heavy components

5. **Accessibility**
   - Use semantic HTML
   - Add ARIA labels
   - Ensure keyboard navigation
   - Touch target minimum 48px

## Migration from Old Code

**Before (Context):**
```tsx
import { useHomeAssistant } from '@/hooks/useHomeAssistant'

const ha = useHomeAssistant()
const entity = ha.getState(entityId)
await ha.toggle(entityId)
```

**After (Entity Store):**
```tsx
import { useEntity } from '@/hooks/useEntity'

const entity = useEntity(entityId)
await entity.toggle()
```

See `docs/MIGRATION.md` for complete migration guide.

## Resources

- [shadcn/ui Documentation](https://ui.shadcn.com/)
- [Atomic Design](https://bradfrost.com/blog/post/atomic-web-design/)
- [Zustand Documentation](https://docs.pmnd.rs/zustand)
- [Tailwind CSS](https://tailwindcss.com/docs)
