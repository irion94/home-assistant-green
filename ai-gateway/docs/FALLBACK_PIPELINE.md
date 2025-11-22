# Fallback Pipeline Architecture

Cascading recognition system - run parallel, use fastest confident result.

## Overview

```
Input → [Tier 1] → [Tier 2] → [Tier 3]
         fast       medium     slow/best

Return first result with confidence > threshold
```

## Pipelines

### 1. STT (Speech-to-Text)

| Tier | Engine | Speed | When to use |
|------|--------|-------|-------------|
| 1 | Vosk | ~100ms | Clear speech, known phrases |
| 2 | Whisper small | ~1s | Vosk confidence < 0.7 |
| 3 | Whisper large | ~3s | Complex/noisy audio |

**Confidence**: Word-level scores from Vosk, perplexity from Whisper

### 2. Intent Recognition

| Tier | Method | Speed | When to use |
|------|--------|-------|-------------|
| 1 | Pattern matcher | ~10ms | Exact command matches |
| 2 | Ollama (qwen2.5:3b) | ~500ms | Pattern fails |
| 3 | OpenAI/Claude API | ~2s | Ollama uncertain |

**Confidence**: Pattern = 1.0, LLM returns confidence in JSON

### 3. TTS (Text-to-Speech)

| Tier | Engine | Speed | When to use |
|------|--------|-------|-------------|
| 1 | VITS (Polish) | ~200ms | Short responses (<20 words) |
| 2 | XTTS v2 | ~10s | Long/conversational responses |

**Routing**: Based on response length and conversation mode

## Implementation

### Phase 1: Intent Pipeline
- [ ] Add confidence to pattern matcher
- [ ] Add confidence to Ollama responses
- [ ] Create parallel executor
- [ ] Add OpenAI fallback (optional)

### Phase 2: STT Pipeline
- [ ] Add Whisper to wake-word service
- [ ] Vosk confidence threshold
- [ ] Parallel Vosk + Whisper execution

### Phase 3: Smart TTS
- [ ] Install XTTS v2
- [ ] Response length router
- [ ] Conversation mode detection

## Code Structure

```
ai-gateway/app/services/
├── pipeline/
│   ├── executor.py      # Parallel execution, early termination
│   ├── stt_pipeline.py  # Vosk → Whisper cascade
│   ├── intent_pipeline.py # Pattern → Ollama → Cloud
│   └── tts_router.py    # VITS vs XTTS selection
```

## Config

```yaml
# docker-compose.yml environment
- STT_CONFIDENCE_THRESHOLD=0.7
- INTENT_CONFIDENCE_THRESHOLD=0.8
- TTS_SHORT_RESPONSE_LIMIT=20
- OPENAI_API_KEY=${OPENAI_API_KEY:-}  # Optional cloud fallback
```

## Progress Log

| Date | Component | Status | Notes |
|------|-----------|--------|-------|
| 2025-01-XX | Design | Done | This document |
| 2025-01-XX | Phase 1 | Done | Intent pipeline with confidence scores |
| 2025-01-XX | Phase 2 | Done | STT pipeline (Vosk → Whisper) |
| 2025-01-XX | Phase 3 | Done | Smart TTS routing (VITS → XTTS) |

### Phase 1 Details (Completed)
- `intent_matcher.py`: Added `match_with_confidence()` returning (action, confidence)
- `ollama_client.py`: Added `translate_command_with_confidence()` extracting confidence from JSON
- `llm_client.py`: Updated system prompt to require confidence (0.0-1.0) in responses
- `json_validator.py`: Added `parse_ollama_response_with_confidence()`
- `pipeline/executor.py`: IntentPipeline runs pattern + LLM in parallel, picks best result
- `gateway.py`: /ask endpoint now uses IntentPipeline with 0.8 confidence threshold

### Phase 2 Details (Completed)
- `stt_client.py`: Added `transcribe_with_confidence()` to base class and `get_stt_pipeline()` factory
- `vosk_client.py`: Extracts word-level confidence from Vosk results, averages them
- `whisper_client.py`: Uses segment avg_logprob converted to probability
- `pipeline/stt_pipeline.py`: STTPipeline tries Vosk first (fast), falls back to Whisper if confidence < 0.7
- `gateway.py`: /voice endpoint now uses STTPipeline with confidence logging

### Phase 3 Details (Completed)
- `wake-word-service/app/tts_service.py`: Smart TTS routing based on response length
  - Short responses (≤15 words) → VITS Polish model (fast, ~200ms)
  - Long responses (>15 words) → XTTS v2 (quality, ~10-30s on CPU)
  - Automatic fallback to VITS if XTTS fails or disabled
  - Configurable threshold via `TTS_SHORT_RESPONSE_LIMIT` env var
  - Lazy model loading (XTTS downloads ~5GB on first use)
  - Language auto-detection for Polish/English
