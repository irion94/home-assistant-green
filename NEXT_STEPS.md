# Next Steps - Voice Assistant Development

**Last Updated:** 2025-11-20
**Current Phase:** Voice Wake-Word Detection ✅ COMPLETE

## Immediate Next Step: Whisper Transcription

### What's Needed
Add audio transcription capability to AI Gateway so recorded voice commands can be converted to text.

### Current Flow (Broken)
```
Voice → Wake-word ✅ → Recording ✅ → AI Gateway ❌ (expects text, gets audio)
```

### Target Flow
```
Voice → Wake-word ✅ → Recording ✅ → Whisper Transcription → Ollama → Home Assistant
```

## Implementation Plan

### 1. Install Whisper in AI Gateway

**File:** `ai-gateway/requirements.txt`
```
openai-whisper>=20231117
```

**Model recommendation:** `base` or `small` (good balance for RPi5)

### 2. Create `/voice` Endpoint

**File:** `ai-gateway/app/routers/gateway.py`

New endpoint that:
- Accepts audio file upload (WAV format)
- Transcribes using Whisper
- Passes transcribed text to existing Ollama pipeline
- Returns same JSON response as `/ask`

### 3. Update Wake-Word Service

**File:** `wake-word-service/app/ai_gateway_client.py`

Change from:
```python
response = httpx.post(f"{base_url}/ask", json={"text": "..."})
```

To:
```python
# Save audio to temp WAV file
# POST audio file to /voice endpoint
response = httpx.post(f"{base_url}/voice", files={"audio": audio_file})
```

### 4. Testing

Test commands:
- "Hey Jarvis, turn on living room lights"
- "Hey Jarvis, what's the temperature?"
- "Hey Jarvis, set bedroom to 20 degrees"

## Monitoring Wake-Word Detection

### Check if it's detecting
```bash
cd ~/home-assistant-green/ai-gateway
docker compose logs -f wake-word | grep "Wake word detected"
```

### View detection confidence
```bash
docker compose logs --tail 50 wake-word | grep "confidence"
```

### Monitor full pipeline
```bash
docker compose logs -f wake-word | grep -E "Wake word|Recording|Sending"
```

## Current Detection Stats

From logs (2025-11-20):
- **Detections:** 6+ successful detections after reboot
- **Confidence:** 90-98% on clear speech
- **Recording:** 7 seconds, 111,360 samples (~7s at 16kHz)
- **False positives:** Very low (0.0000-0.0020 on ambient noise)

## Service Status

All services running:
```
✅ homeassistant  - Up 3 minutes
✅ ai-gateway     - Up 3 minutes (healthy)
✅ mosquitto      - Up 3 minutes (healthy)
✅ wake-word      - Up 3 minutes (healthy)
```

## Documentation

- **Full Progress:** `docs/WAKE_WORD_PROGRESS.md`
- **Architecture:** `docs/VOICE_WAKEWORD_ARCHITECTURE.md`
- **Project Guide:** `/home/irion94/CLAUDE.md`
- **Main README:** `README.md`

## Quick Commands

### Restart wake-word service
```bash
cd ~/home-assistant-green/ai-gateway
docker compose restart wake-word
```

### View service logs
```bash
docker compose logs --tail 100 wake-word
```

### Rebuild after code changes
```bash
docker compose up -d --build wake-word
```

### Check all services
```bash
docker compose ps
```

## Estimated Timeline

- **Whisper Integration:** 1-2 hours
- **Testing & Tuning:** 1 hour
- **Total to working voice assistant:** 2-3 hours

## Success Criteria

When complete, you should be able to:
1. Say "Hey Jarvis" → system detects and starts recording
2. Speak command → system transcribes with Whisper
3. Command processed → Ollama extracts intent
4. Action executed → Home Assistant controls devices
5. (Optional) Voice/visual feedback confirms action

---

**Status:** Ready to proceed with Whisper integration
**Blockers:** None
**Next Action:** Implement `/voice` endpoint with Whisper transcription
