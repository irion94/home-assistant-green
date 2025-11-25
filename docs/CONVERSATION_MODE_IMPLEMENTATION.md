# Conversation Mode Implementation Plan

## Current Problem

Wake-word always enters multi-turn conversation mode, showing incorrect status "waiting for wake word" while conversing.

## Desired Behavior

1. **Default (Single Command)**: Wake-word → modal opens → one command → auto-close
2. **Conversation Mode Toggle**: User enables toggle → multi-turn conversation until "koniec" or manual close

## Implementation Plan

### 1. Add Single-Command Mode to Wake-Word Service

**File**: `wake-word-service/app/main.py`

- Create new method `process_single_command()`:
  - Record audio (7-10 seconds)
  - Transcribe with parallel STT (Vosk + Whisper timeout)
  - Send to `/conversation` endpoint (NOT conversation loop)
  - Play TTS response once
  - Return to idle

- Modify wake-word detection handler (line ~762):
  - Check if conversation mode enabled (from env var or MQTT)
  - If `CONVERSATION_MODE=false`: Call `process_single_command()`
  - If `CONVERSATION_MODE=true`: Call `run_conversation_loop()` (current behavior)

- Add MQTT subscription for conversation mode toggle:
  - Topic: `voice_assistant/config/conversation_mode` (true/false)
  - Store in instance variable
  - Allow runtime toggle from kiosk

### 2. Add Conversation Mode Toggle to VoiceOverlay

**File**: `react-dashboard/src/components/kiosk/VoiceOverlay.tsx`

- Add toggle switch in header:
  - Label: "Conversation Mode"
  - Position: Top-right corner near close button
  - State persisted to localStorage
  - Publishes to MQTT when changed

- Update status display logic:
  - Show "Single Command Mode" vs "Conversation Mode" in status
  - Remove auto-close timer when conversation mode enabled
  - Add 3-second auto-close timer after TTS in single-command mode

### 3. Update MQTT Service

**File**: `react-dashboard/src/services/mqttService.ts`

- Add method: `setConversationMode(enabled: boolean)`
- Publishes to: `voice_assistant/config/conversation_mode`
- Subscribe to topic for sync across devices

### 4. Environment Configuration

**File**: `ai-gateway/docker-compose.yml`

- Add env var: `CONVERSATION_MODE_DEFAULT=false` (single-command by default)
- Can be overridden via MQTT toggle

## Files to Modify

1. `/home/irion94/home-assistant-green/wake-word-service/app/main.py` - Add single-command mode
2. `/home/irion94/home-assistant-green/react-dashboard/src/components/kiosk/VoiceOverlay.tsx` - Add toggle UI
3. `/home/irion94/home-assistant-green/react-dashboard/src/services/mqttService.ts` - Add config publish method
4. `/home/irion94/home-assistant-green/ai-gateway/docker-compose.yml` - Add default config

## Expected Flow After Fix

### Single Command (default)

```
User: "Hey Jarvis"
→ Modal opens with toggle OFF
→ User: "Turn on lights"
→ Status: listening → processing → speaking
→ Response plays
→ Auto-close after 3 seconds
```

### Conversation Mode (toggle ON)

```
User: "Hey Jarvis"
→ Modal opens with toggle ON
→ User: "Let's talk"
→ Status: conversation mode active
→ Multi-turn dialogue
→ User: "End" or manual close
→ Modal closes
```

## Technical Details

### Current Wake-Word Detection Flow

**Path A: Streaming Single Command (lines 549-701)**
- `process_wake_word_detection()` method
- Records audio → sends to `/voice/stream` endpoint
- Plays TTS response via streaming
- **OLD implementation** - currently bypassed

**Path B: Direct Conversation Mode (lines 404-539)**
- `run_conversation_loop()` method
- **Currently triggered immediately** after wake-word detection
- Continuous loop until end keywords or timeout
- This is what causes the issue

### Wake-Word Service Current Triggers

1. Wake-word detection → **Direct to conversation loop** (line 762-772)
2. MQTT `start_conversation` command (lines 726-734)
3. End of streaming response if conversation flag set (lines 683-694)

### Conversation Loop End Conditions

- End keywords detected: "stop", "koniec", "bye", "zakończ", etc. (line 483-489)
- MQTT stop command received (line 417-421)
- Timeout: 30s default (line 424-427)

### Status Messages

- `idle` - Waiting for wake word
- `listening` - Recording user speech (red pulsing)
- `processing` - Transcribing/LLM processing (yellow spinner)
- `speaking` - TTS playing (green pulse)
- `conversation` - Conversation mode active (blue)

### MQTT Topics

**Current:**
- `voice_assistant/status` - Current status string
- `voice_assistant/transcript` - User speech transcription
- `voice_assistant/response` - AI response text
- `voice_assistant/command` - Commands (start_conversation, stop_conversation)
- `voice_assistant/stt_comparison` - Vosk vs Whisper comparison

**New:**
- `voice_assistant/config/conversation_mode` - Boolean toggle for conversation mode

## Implementation Steps

1. **Wake-Word Service**
   - Add `conversation_mode_enabled` instance variable
   - Subscribe to MQTT config topic
   - Implement `process_single_command()` method
   - Modify wake-word handler to choose mode

2. **React Dashboard**
   - Add toggle component to VoiceOverlay
   - Store toggle state in localStorage
   - Publish changes to MQTT
   - Update status display logic

3. **MQTT Service**
   - Add `setConversationMode()` method
   - Handle config topic subscription

4. **Docker Config**
   - Add default conversation mode env var

5. **Testing**
   - Test single-command flow with auto-close
   - Test conversation mode with toggle enabled
   - Test toggle persistence across page reloads
   - Test MQTT sync across devices
