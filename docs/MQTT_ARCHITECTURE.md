# MQTT Architecture

**Phase 5: MQTT Decoupling**
**Last Updated**: 2025-12-01

---

## Overview

The MQTT messaging system provides real-time communication between the voice assistant backend (AI Gateway, Wake-Word Service) and the React Dashboard frontend. All topics use a centralized configuration with versioning support for graceful migrations.

---

## Topic Structure

All topics follow this hierarchical pattern:

```
{version}/{base_prefix}/room/{room_id}/session/{session_id}/{topic_type}
```

### Components

- **version**: API version prefix (e.g., `v1`, `v2`) - allows breaking changes without disruption
- **base_prefix**: Namespace for voice assistant topics (default: `voice_assistant`)
- **room_id**: Physical room identifier (e.g., `salon`, `bedroom`, `kitchen`)
- **session_id**: Unique session identifier (UUID format)
- **topic_type**: Specific message type (see below)

### Example Topics

```
v1/voice_assistant/room/salon/session/abc-123/state
v1/voice_assistant/room/salon/session/abc-123/display_action
v1/voice_assistant/room/bedroom/session/xyz-456/response
```

---

## Configuration

### Backend (Python)

File: `ai-gateway/app/config/mqtt_topics.py`

```python
from app.config.mqtt_topics import get_mqtt_config

topics = get_mqtt_config()
topic = topics.display_action(room_id="salon", session_id="abc-123")
# Returns: "v1/voice_assistant/room/salon/session/abc-123/display_action"
```

**Environment Variables**:
- `MQTT_TOPIC_VERSION`: Version prefix (default: `v1`)
- `MQTT_BASE_PREFIX`: Base namespace (default: `voice_assistant`)

### Frontend (TypeScript)

File: `react-dashboard/src/config/mqttTopics.ts`

```typescript
import { mqttTopics } from '@/config/mqttTopics'

const topic = mqttTopics.displayAction('salon', 'abc-123')
// Returns: "v1/voice_assistant/room/salon/session/abc-123/display_action"
```

**Environment Variables**:
- `VITE_MQTT_TOPIC_VERSION`: Version prefix (default: `v1`)
- `VITE_MQTT_BASE_PREFIX`: Base namespace (default: `voice_assistant`)

---

## Topic Types

| Topic Type | Direction | Purpose | Payload Example |
|------------|-----------|---------|-----------------|
| `/state` | Backend → Frontend | Voice assistant state changes | `{"state": "listening", "timestamp": 123}` |
| `/transcript` | Backend → Frontend | Final user transcript (legacy) | `{"text": "turn on lights", "timestamp": 123}` |
| `/transcript/interim` | Backend → Frontend | Streaming STT interim results | `{"text": "turn on", "sequence": 1, "timestamp": 123}` |
| `/transcript/final` | Backend → Frontend | Vosk final transcript | `{"text": "turn on lights", "confidence": 0.85, "timestamp": 123}` |
| `/transcript/refined` | Backend → Frontend | Whisper-refined transcript | `{"text": "Turn on the lights", "timestamp": 123}` |
| `/response` | Backend → Frontend | Complete AI response | `{"text": "Turning on the lights", "timestamp": 123}` |
| `/response/stream/start` | Backend → Frontend | Streaming response started | `{"timestamp": 123}` |
| `/response/stream/chunk` | Backend → Frontend | Token-by-token streaming | `{"chunk": " lights", "timestamp": 123}` |
| `/response/stream/complete` | Backend → Frontend | Streaming complete | `{"timestamp": 123}` |
| `/display_action` | Backend → Frontend | UI panel switching | `{"type": "light_control", "data": {...}, "timestamp": 123}` |
| `/tool_executed` | Backend → Frontend | Tool execution events | `{"tool_name": "control_light", "success": true, "timestamp": 123}` |
| `/overlay_hint` | Backend → Frontend | Overlay behavior hints | `{"keep_open": true, "timestamp": 123}` |

---

## Subscription Patterns

### Wildcards

MQTT supports two wildcard characters:
- **+**: Matches a single level (e.g., `room/+/state` → `room/salon/state` ✓, `room/salon/session/1` ✗)
- **#**: Matches multiple levels (e.g., `room/#` → `room/salon/state` ✓, `room/salon/session/1/state` ✓)

### Common Subscriptions

```typescript
// Subscribe to all sessions in a room (React Dashboard)
mqttTopics.subscribeAllSessions('salon')
// Returns: "v1/voice_assistant/room/salon/session/+/#"

// Subscribe to specific session
mqttTopics.subscribeSession('salon', 'abc-123')
// Returns: "v1/voice_assistant/room/salon/session/abc-123/#"
```

---

## Version Migration

### Why Versioning?

Topic versioning allows breaking changes (e.g., payload format, hierarchy changes) without disrupting production systems. During migration, both old and new versions coexist.

### Migration Process

**Example: Migrating from v0 (legacy) to v1 (versioned)**

#### Step 1: Backend Dual Publishing (Week 1)

Publish to both v0 and v1 topics:

```python
# ai-gateway/app/services/mqtt_client.py
topic_v1 = self.topics.display_action(room_id, session_id)
topic_v0 = self.topics.legacy_display_action(room_id, session_id)

self.client.publish(topic_v1, payload)  # v1 (new)
self.client.publish(topic_v0, payload)  # v0 (legacy)
```

#### Step 2: Frontend Dual Subscription (Week 1)

Subscribe to both versions:

```typescript
// react-dashboard/src/services/mqttService.ts
const topics = [
  mqttTopics.subscribeAllSessions(roomId),        // v1 (new)
  mqttTopics.subscribeLegacySessions(roomId),     // v0 (legacy)
]
client.subscribe(topics)
```

#### Step 3: Monitor v0 Usage (Week 2)

Check logs for v0 topic usage:

```bash
docker compose logs ai-gateway | grep "v0 topic"
# Should see decreasing frequency as frontend migrates to v1
```

#### Step 4: Drop v0 Support (Week 3)

Remove legacy topic publishing:

```python
# Remove this line after 2-week migration period:
# self.client.publish(topic_v0, payload)
```

### Rollback Procedure

If v1 causes issues, temporarily revert:

```bash
# Backend: Force v0 topic format
export MQTT_TOPIC_VERSION=""  # Empty = v0 (no version prefix)
docker compose restart ai-gateway

# Frontend: Disable v1 subscription
export VITE_MQTT_TOPIC_VERSION=""
docker compose restart react-dashboard
```

---

## Testing Without Live Broker

### Backend (Python)

Use `MockMQTTClient` from `tests/mocks/mqtt_client.py`:

```python
from tests.mocks.mqtt_client import get_mock_mqtt_client

def test_display_action_published():
    mock_mqtt = get_mock_mqtt_client()

    # Your code that publishes to MQTT
    tool.execute(mqtt_client=mock_mqtt)

    # Verify message published
    messages = mock_mqtt.get_published_to("*/display_action")
    assert len(messages) == 1
    assert "light_control" in messages[0]["payload"]
```

### Frontend (TypeScript)

Mock MQTT.js in Vitest:

```typescript
import { vi } from 'vitest'

vi.mock('mqtt', () => ({
  connect: vi.fn(() => ({
    on: vi.fn(),
    subscribe: vi.fn(),
    publish: vi.fn(),
  })),
}))
```

---

## Message Flow Examples

### Example 1: Voice Command (Wake-Word Trigger)

```
1. Wake-Word Service → MQTT
   Topic: v1/voice_assistant/room/salon/session/abc-123/state
   Payload: {"state": "wake_detected", "timestamp": 1701234567890}

2. Wake-Word Service → MQTT
   Topic: v1/voice_assistant/room/salon/session/abc-123/transcript/final
   Payload: {"text": "turn on lights", "confidence": 0.87, "timestamp": 1701234567891}

3. AI Gateway → MQTT
   Topic: v1/voice_assistant/room/salon/session/abc-123/state
   Payload: {"state": "processing", "timestamp": 1701234567892}

4. AI Gateway → MQTT (Tool Execution)
   Topic: v1/voice_assistant/room/salon/session/abc-123/display_action
   Payload: {"type": "light_control", "data": {...}, "timestamp": 1701234567893}

5. AI Gateway → MQTT
   Topic: v1/voice_assistant/room/salon/session/abc-123/response
   Payload: {"text": "Turning on the lights", "timestamp": 1701234567894}
```

### Example 2: Streaming Response

```
1. AI Gateway → MQTT (Start)
   Topic: v1/voice_assistant/room/salon/session/abc-123/response/stream/start
   Payload: {"timestamp": 1701234567890}

2. AI Gateway → MQTT (Chunk 1)
   Topic: v1/voice_assistant/room/salon/session/abc-123/response/stream/chunk
   Payload: {"chunk": "Turning", "timestamp": 1701234567891}

3. AI Gateway → MQTT (Chunk 2)
   Topic: v1/voice_assistant/room/salon/session/abc-123/response/stream/chunk
   Payload: {"chunk": " on", "timestamp": 1701234567892}

4. AI Gateway → MQTT (Complete)
   Topic: v1/voice_assistant/room/salon/session/abc-123/response/stream/complete
   Payload: {"timestamp": 1701234567900}
```

---

## Troubleshooting

### Issue: Messages Not Received

**Symptoms**: Frontend doesn't update, backend logs show successful publish

**Diagnosis**:
```bash
# Subscribe to all topics via mosquitto_sub
docker compose exec mosquitto mosquitto_sub -t "#" -v

# Check if messages arrive on broker
```

**Common Causes**:
- **Version mismatch**: Backend publishes v1, frontend subscribes v0 (or vice versa)
- **Room ID mismatch**: Frontend subscribes to wrong room
- **Wildcard error**: Incorrect use of + or # in subscription

**Solution**:
```bash
# Check environment variables
docker compose exec ai-gateway env | grep MQTT_TOPIC_VERSION
docker compose exec react-dashboard env | grep VITE_MQTT_TOPIC_VERSION

# Should both return "v1" during normal operation
```

### Issue: Hardcoded Topics

**Symptoms**: Topics don't respect environment variables

**Diagnosis**:
```bash
# Search for hardcoded topic strings
grep -r "voice_assistant/room" --include="*.py" --include="*.ts" ai-gateway/ react-dashboard/

# Should only return config files and comments
```

**Fix**: Replace hardcoded strings with config methods:
```python
# Before:
topic = f"voice_assistant/room/{room_id}/session/{session_id}/state"

# After:
topic = self.topics.state(room_id, session_id)
```

---

## Performance Considerations

### Message Frequency

- **State changes**: ~5-10 per conversation (low frequency)
- **Streaming transcripts**: ~10-20 per second during speech (high frequency)
- **Streaming responses**: ~20-30 per second during AI response (high frequency)

### QoS Levels

Current implementation uses **QoS 1** (at least once delivery) for all messages:

```python
self.client.publish(topic, payload, qos=1)
```

**Rationale**:
- QoS 0 (at most once): Too unreliable for critical state updates
- QoS 1 (at least once): Balances reliability and performance ✓
- QoS 2 (exactly once): Unnecessary overhead for idempotent messages

### Payload Size

Keep payloads small for performance:
- **State updates**: ~50-100 bytes ✓
- **Transcripts**: ~200-500 bytes ✓
- **Streaming chunks**: ~10-50 bytes ✓
- **Display actions**: ~500-2000 bytes (acceptable for infrequent use)

**Warning**: Avoid embedding large data (images, audio) in MQTT messages. Use HTTP endpoints for bulk data.

---

## Future Enhancements

### Planned Features

1. **v2 Topics** (Future):
   - Add compression for large payloads
   - Separate topic hierarchy for multi-room scenarios
   - Schema validation with JSON Schema

2. **Retained Messages**:
   - Persist last state for late-joining clients
   - Useful for mobile app reconnects

3. **Topic ACLs**:
   - Restrict which services can publish to which topics
   - Improve security in multi-tenant scenarios

---

## Related Documentation

- **Testing Guide**: `/docs/TESTING.md`
- **Migration Plan**: `/.claude/plans/phase-05-mqtt-decoupling.md`
- **Security**: `/docs/SECURITY.md`

---

**Phase 5 Complete**: All MQTT topics centralized, versioned, and testable.
