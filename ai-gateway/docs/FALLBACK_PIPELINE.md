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

### Phase 5: Input Validation & Personality ✅
Smart input validation + refined Jarvis personality.

**Goal**: Filter gibberish before AI, define consistent Jarvis character.

#### 5.1 Text Validator
- [x] Validate transcribed text before AI fallback
- [x] Check minimum word count (≥2 words)
- [x] Detect gibberish/noise (single chars, no real words)
- [x] Short Polish responses: "Nie rozumiem"

#### 5.2 Jarvis Personality
- [x] Friendly but minimalist responses
- [x] Always respond in Polish (unless asked in English)
- [x] Short acknowledgments for simple actions
- [x] Natural, conversational tone

#### Files to modify:

**gateway.py** - Add text validator:
```python
def is_valid_input(text: str) -> bool:
    """Check if text is meaningful enough for AI."""
    words = text.split()
    if len(words) < 2:
        return False
    # Check for actual words (not just noise)
    if all(len(w) <= 2 for w in words):
        return False
    return True

# In /voice endpoint, before AI fallback:
if action.action == "none":
    if not is_valid_input(text):
        return AskResponse(
            status="success",
            message="Nie rozumiem",
        )
    # Fall back to AI...
```

**conversation_client.py** - Update system prompt:
```python
CONVERSATION_SYSTEM_PROMPT = """Jesteś Jarvis - przyjazny asystent domowy.

Zasady:
1. ZAWSZE odpowiadaj po polsku (chyba że użytkownik pyta po angielsku)
2. Bądź zwięzły - krótkie odpowiedzi dla prostych pytań
3. Bądź przyjazny i naturalny, nie robotyczny
4. Dla potwierdzeń akcji: tylko "Gotowe" lub krótka odpowiedź
5. Dla pytań: 1-3 zdania, konkretnie i na temat

Przykłady dobrych odpowiedzi:
- "Jaka jest pogoda?" → "Nie mam dostępu do pogody, ale mogę pomóc skonfigurować czujnik."
- "Opowiedz żart" → "Dlaczego programista nosi okulary? Bo nie widzi C#!"
- "Dziękuję" → "Nie ma za co!"
"""
```

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

### Phase 6: Streaming TTS ✅
Stream AI responses to TTS for reduced latency.

**Goal**: Start speaking while AI is still generating, reducing perceived wait time.

**Current flow** (~2-4s total wait):
```
User speaks → STT → AI (wait 1-3s) → Full response → TTS synthesis → Play
```

**Target flow** (~0.5-1s to first audio):
```
User speaks → STT → AI streams → First sentence ready → TTS plays
                              → Second sentence ready → Queue TTS
                              → ...continues...
```

#### 6.1 Sentence-based Streaming
- [x] Stream AI response chunks
- [x] Buffer until sentence boundary (. ! ?)
- [x] Send complete sentence to TTS immediately
- [x] Queue subsequent sentences

#### 6.2 TTS Queue Management
- [x] Implement TTS queue in wake-word service
- [x] Play sentences sequentially without gaps
- [x] Handle interrupts (stop current + clear queue)
- [x] Fallback to full response if streaming fails

#### 6.3 Gateway Streaming Endpoint
- [x] Create `/voice/stream` endpoint with SSE
- [x] Stream sentence chunks as they complete
- [x] Include sentence index for ordering
- [x] Handle connection drops gracefully

#### Files to modify:

**conversation_client.py** - Sentence streaming:
```python
async def chat_stream_sentences(self, text: str, session_id: str) -> AsyncIterator[str]:
    """Stream response sentence by sentence."""
    buffer = ""
    sentence_endings = {'.', '!', '?'}

    async for chunk in self.chat_stream(text, session_id):
        buffer += chunk

        # Check for complete sentence
        for i, char in enumerate(buffer):
            if char in sentence_endings:
                # Check if it's really end of sentence (not abbreviation)
                if i + 1 < len(buffer) and buffer[i + 1] == ' ':
                    sentence = buffer[:i + 1].strip()
                    buffer = buffer[i + 2:]
                    if sentence:
                        yield sentence
                    break

    # Yield remaining buffer
    if buffer.strip():
        yield buffer.strip()
```

**gateway.py** - SSE streaming endpoint:
```python
from fastapi.responses import StreamingResponse

@router.post("/voice/stream")
async def voice_stream(
    audio: UploadFile = File(...),
    # ... dependencies
):
    async def generate():
        # Transcribe audio
        text = await stt_pipeline.transcribe(audio_bytes)

        # Stream sentences
        async for sentence in conversation_client.chat_stream_sentences(text, session_id):
            yield f"data: {json.dumps({'sentence': sentence})}\\n\\n"

        yield "data: [DONE]\\n\\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

**wake-word main.py** - TTS queue:
```python
import queue
import threading

class TTSQueue:
    def __init__(self, tts_service):
        self.tts_service = tts_service
        self.queue = queue.Queue()
        self.playing = False
        self.worker = threading.Thread(target=self._worker, daemon=True)
        self.worker.start()

    def _worker(self):
        while True:
            sentence = self.queue.get()
            if sentence is None:
                break
            self.playing = True
            self.tts_service.speak(sentence)
            self.playing = False

    def add(self, sentence: str):
        self.queue.put(sentence)

    def clear(self):
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break

# In process_wake_word_detection:
async with httpx.AsyncClient() as client:
    async with client.stream("POST", f"{url}/voice/stream", files=files) as response:
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data = line[6:]
                if data == "[DONE]":
                    break
                sentence = json.loads(data)["sentence"]
                tts_queue.add(sentence)
```

#### Expected Improvements:
- **First word latency**: 2-4s → 0.5-1s
- **Perceived responsiveness**: Much better
- **User can interrupt**: Yes (clear queue)

#### Risks:
- Sentence detection edge cases (abbreviations, numbers)
- TTS gaps between sentences
- Network issues during streaming

## Progress Log

| Date | Component | Status | Notes |
|------|-----------|--------|-------|
| 2025-01-XX | Phase 1 | Done | Intent pipeline with confidence |
| 2025-01-XX | Phase 2 | Done | STT pipeline (Vosk → Whisper) |
| 2025-01-XX | Phase 3 | Done | Smart TTS (VITS → XTTS) |
| 2025-11-22 | Phase 4.1 | Done | Smart fallback to AI |
| 2025-11-22 | Phase 4.2 | Done | Actions in conversation |
| 2025-11-22 | Phase 5.1 | Done | Text validator |
| 2025-11-22 | Phase 5.2 | Done | Jarvis personality |
| 2025-11-22 | Phase 6 | Done | Streaming TTS |

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
