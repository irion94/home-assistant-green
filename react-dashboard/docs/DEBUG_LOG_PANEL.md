# Debug Log Panel for VoiceOverlay

## Goal

Add a scrolling terminal-style debug log to VoiceOverlay showing:
- Timing/latency metrics (STT, LLM, TTS durations)
- State transitions with timestamps
- Raw MQTT messages as they arrive

## UI Design

```
┌─────────────────────────────────────────────────────────┐
│  [Header: Connection, Room, Session, Conv Mode Button]  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [Messages Area - Chat bubbles]                         │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  [Status Indicator - Mic icon, state label]             │
├─────────────────────────────────────────────────────────┤
│  ▼ Debug Log                                    [Clear] │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 12:34:56.123 [STATE] idle → wake_detected         │  │
│  │ 12:34:56.234 [MQTT] session/active = "abc123"     │  │
│  │ 12:34:56.345 [STATE] wake_detected → listening    │  │
│  │ 12:34:58.456 [MQTT] transcript = "włącz światło"  │  │
│  │ 12:34:58.567 [TIMING] STT: 2.1s (vosk)            │  │
│  │ 12:34:58.678 [STATE] listening → processing       │  │
│  │ 12:34:59.789 [MQTT] response = "Gotowe"           │  │
│  │ 12:34:59.890 [TIMING] LLM: 1.2s                   │  │
│  │ 12:35:00.001 [STATE] processing → speaking        │  │
│  │ ▼ (auto-scroll to bottom)                         │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## Implementation

### 1. Add Debug Log State to voiceStore

**File:** `src/stores/voiceStore.ts`

```typescript
interface DebugLogEntry {
  id: string
  timestamp: Date
  type: 'STATE' | 'MQTT' | 'TIMING' | 'ERROR'
  message: string
}

// Add to store state:
debugLogs: DebugLogEntry[]
debugEnabled: boolean  // Persisted to localStorage

// Add actions:
addDebugLog: (type, message) => void
clearDebugLogs: () => void
toggleDebug: () => void
```

### 2. Hook MQTT Service to Emit Debug Logs

**File:** `src/services/mqttService.ts`

Add `store.addDebugLog()` calls at key points:
- When MQTT message received (topic + truncated payload)
- When state changes
- When session starts/ends
- When STT comparison arrives (with timing)

```typescript
// Example in handleRoomMessage():
store.addDebugLog('MQTT', `${subTopic} = ${payload.slice(0, 50)}...`)
store.addDebugLog('STATE', `${prevState} → ${newState}`)
store.addDebugLog('TIMING', `STT: ${comparison.vosk.duration}s (${comparison.selected})`)
```

### 3. Create DebugLogPanel Component

**File:** `src/components/kiosk/DebugLogPanel.tsx` (NEW)

```tsx
export function DebugLogPanel() {
  const { debugLogs, debugEnabled, clearDebugLogs } = useVoiceStore()
  const logEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new logs
  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [debugLogs])

  if (!debugEnabled) return null

  return (
    <div className="border-t border-surface-light/30 p-2">
      <div className="flex justify-between items-center mb-2">
        <span className="text-xs text-text-secondary">▼ Debug Log</span>
        <button onClick={clearDebugLogs} className="text-xs hover:text-error">
          Clear
        </button>
      </div>
      <div className="h-32 overflow-y-auto bg-black/50 rounded font-mono text-xs p-2">
        {debugLogs.map(log => (
          <div key={log.id} className={logTypeColor(log.type)}>
            <span className="text-text-secondary">{formatTime(log.timestamp)}</span>
            {' '}
            <span className="font-bold">[{log.type}]</span>
            {' '}
            {log.message}
          </div>
        ))}
        <div ref={logEndRef} />
      </div>
    </div>
  )
}

const logTypeColor = (type: string) => ({
  STATE: 'text-info',
  MQTT: 'text-success',
  TIMING: 'text-warning',
  ERROR: 'text-error',
}[type] || 'text-text-primary')
```

### 4. Add Toggle Button to VoiceOverlay Header

**File:** `src/components/kiosk/VoiceOverlay.tsx`

Add a bug icon debug toggle button next to the close button:

```tsx
<button
  onClick={() => useVoiceStore.getState().toggleDebug()}
  className={cn(
    "p-2 rounded-full",
    debugEnabled ? "bg-warning/30 text-warning" : "bg-surface-light/30"
  )}
  title="Toggle debug log"
>
  <Bug className="w-5 h-5" />
</button>
```

### 5. Render DebugLogPanel in VoiceOverlay

At the bottom of VoiceOverlay (after status indicator section):

```tsx
{/* Debug Log Panel */}
<DebugLogPanel />
```

## Files to Modify

| File | Changes |
|------|---------|
| `voiceStore.ts` | Add `debugLogs`, `debugEnabled`, actions |
| `mqttService.ts` | Add `store.addDebugLog()` calls at key points |
| `DebugLogPanel.tsx` | NEW: Scrolling log component |
| `VoiceOverlay.tsx` | Add debug toggle button + render DebugLogPanel |

## Log Entry Types

| Type | Color | When Logged |
|------|-------|-------------|
| `STATE` | Blue | State machine transitions |
| `MQTT` | Green | Raw MQTT messages (topic + payload) |
| `TIMING` | Yellow | STT duration, LLM latency, TTS duration |
| `ERROR` | Red | Errors, connection failures |

## Performance Considerations

- Limit to last 100 log entries (FIFO)
- Truncate long payloads (50 chars + "...")
- Don't persist logs to localStorage (memory only)
