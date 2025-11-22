# Fallback Pipeline Architecture

Cascading recognition system with unified voice assistant.

## Overview

```
Voice Input → STT → Intent Pipeline → Action found?
                                         ↓
                              yes ←──────┴──────→ no
                               ↓                   ↓
                          Execute HA           Ask AI
                               ↓                   ↓
                           "Gotowe"          AI response
                                                   ↓
                                              TTS speak
```

## Pipelines

### 1. STT (Speech-to-Text)

| Tier | Engine | Speed | When to use |
|------|--------|-------|-------------|
| 1 | Vosk | ~100ms | Clear speech, known phrases |
| 2 | Whisper | ~1s | Vosk confidence < 0.7 |

### 2. Intent Recognition

| Tier | Method | Speed | When to use |
|------|--------|-------|-------------|
| 1 | Pattern matcher | ~10ms | Exact command matches |
| 2 | Ollama LLM | ~500ms | Pattern fails |
| 3 | AI fallback | ~1s | No HA action → treat as question |

### 3. TTS (Text-to-Speech)

| Tier | Engine | Speed | When to use |
|------|--------|-------|-------------|
| 1 | VITS (Polish) | ~200ms | Short responses (≤15 words) |
| 2 | XTTS v2 | ~10s | Long responses (>15 words) |

## Implementation Phases

### Phase 1: Intent Pipeline ✅
- [x] Add confidence to pattern matcher
- [x] Add confidence to Ollama responses
- [x] Create parallel executor
- [x] Polish TTS messages

### Phase 2: STT Pipeline ✅
- [x] Vosk → Whisper cascade
- [x] Confidence threshold (0.7)
- [x] Pipeline integration

### Phase 3: Smart TTS ✅
- [x] VITS for short responses
- [x] XTTS v2 for long responses
- [x] Word count routing (15 words)

### Phase 4: Unified Assistant ✅
Smart fallback + actions in conversation.

**Goal**: No more "no action available" - always respond intelligently.

#### 4.1 Smart Fallback (voice commands)
- [x] Detect when no HA action matches
- [x] Fall back to conversation AI
- [x] Return AI response for TTS
- [x] Update response model for hybrid results

#### 4.2 Actions in Conversation
- [x] Check each conversation message for HA actions
- [x] If action found → execute + acknowledge
- [x] Continue conversation after action
- [x] Natural flow: "Turn on lights" → executes → "Gotowe. ..."

## Code Structure

```
ai-gateway/app/
├── services/
│   ├── pipeline/
│   │   ├── executor.py      # Intent pipeline
│   │   └── stt_pipeline.py  # STT pipeline
│   ├── conversation_client.py  # AI conversation
│   └── ha_client.py         # HA service calls
├── routers/
│   └── gateway.py           # /voice, /conversation endpoints
└── models.py                # Response models

wake-word-service/app/
├── main.py                  # Detection loop
└── tts_service.py           # Smart TTS routing
```

## Config

```yaml
# Confidence thresholds
STT_CONFIDENCE_THRESHOLD=0.7
INTENT_CONFIDENCE_THRESHOLD=0.8

# TTS routing
TTS_SHORT_RESPONSE_LIMIT=15

# Models
OLLAMA_MODEL=qwen2.5:3b
WHISPER_MODEL=small
```

## Progress Log

| Date | Component | Status | Notes |
|------|-----------|--------|-------|
| 2025-01-XX | Phase 1 | Done | Intent pipeline with confidence |
| 2025-01-XX | Phase 2 | Done | STT pipeline (Vosk → Whisper) |
| 2025-01-XX | Phase 3 | Done | Smart TTS (VITS → XTTS) |
| 2025-11-22 | Phase 4.1 | Done | Smart fallback to AI |
| 2025-11-22 | Phase 4.2 | Done | Actions in conversation |

### Phase 1-3 Details (Completed)

**Intent Pipeline**:
- `intent_matcher.py`: `match_with_confidence()` with fuzzy matching
- `ollama_client.py`: `translate_command_with_confidence()`
- `pipeline/executor.py`: IntentPipeline parallel execution

**STT Pipeline**:
- `vosk_client.py`: Word-level confidence extraction
- `whisper_client.py`: Segment log probability
- `pipeline/stt_pipeline.py`: Vosk-first with Whisper fallback

**Smart TTS**:
- `tts_service.py`: VITS (≤15 words) / XTTS (>15 words)
- Polish response messages ("Gotowe", "Nie wykryto mowy")
- Auto language detection

### Phase 4 Implementation Plan

#### Files to modify:

**gateway.py**:
```python
# /voice endpoint - add AI fallback
if action.action == "none" or not action:
    # Fall back to conversation AI
    response_text = await conversation_client.chat(text, "voice_fallback")
    return AskResponse(
        status="success",
        message=response_text,  # AI response for TTS
        plan=None,
    )
```

**conversation_client.py**:
```python
# Check for HA actions in conversation
async def chat(self, message: str, session_id: str):
    # First check if this is an HA command
    action = intent_matcher.match(message)
    if action and action.action != "none":
        # Execute action
        await ha_client.call_service(action)
        # Acknowledge and continue
        return f"Gotowe. {await self._get_ai_response(message)}"

    # Normal conversation
    return await self._get_ai_response(message)
```

**models.py**:
```python
class AskResponse(BaseModel):
    status: str
    message: str | None = None      # For TTS (Polish)
    text: str | None = None         # AI response text
    plan: HAAction | None = None
    ha_response: dict | None = None
```

**main.py (wake-word)**:
```python
# Handle hybrid response
response_text = response.get("text") or response.get("message")
if response_text:
    self.tts_service.speak(response_text)
```
