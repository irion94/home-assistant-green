# Voice Wake-Word Detection Architecture

## Hardware Setup

**Microphone**: ReSpeaker 4 Mic Array (UAC1.0) by Seeed
- **Device**: `hw:2,0` → `/dev/snd/pcmC2D0c`
- **Channels**: 6 (4 microphones + 2 processed outputs)
- **Sample Rate**: 16000 Hz
- **Format**: 16-bit signed little-endian (S16_LE)
- **Status**: ✅ Verified working

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Raspberry Pi 5                          │
│                                                             │
│  ┌──────────────┐     ┌──────────────┐     ┌────────────┐ │
│  │  ReSpeaker   │────▶│  Wake-Word   │────▶│ AI Gateway │ │
│  │  4 Mic Array │     │   Service    │     │  (FastAPI) │ │
│  │  (hw:2,0)    │     │ (OpenWakeWord│     │            │ │
│  └──────────────┘     │   Docker)    │     └────────────┘ │
│                       └──────────────┘            │        │
│                              │                    │        │
│                              ▼                    ▼        │
│                       ┌──────────────┐     ┌────────────┐ │
│                       │   Audio      │     │   Ollama   │ │
│                       │  Feedback    │     │  (LLM)     │ │
│                       │  (Beep/LED)  │     └────────────┘ │
│                       └──────────────┘            │        │
│                                                   ▼        │
│                                            ┌────────────┐  │
│                                            │    Home    │  │
│                                            │  Assistant │  │
│                                            └────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Wake-Word Detection Service
- **Technology**: OpenWakeWord (open-source, Raspberry Pi optimized)
- **Base Image**: Python 3.11 Alpine Linux
- **Audio Library**: PyAudio
- **Wake Word Models**: "Hey Jarvis" (pre-trained)
- **Detection Threshold**: 0.5 (adjustable)

### Integration Components
- **Transcription**: Whisper (faster-whisper for speed)
- **Intent Extraction**: Ollama (qwen2.5:3b)
- **Action Execution**: Home Assistant REST API
- **Feedback**: Audio beeps + optional LED

## Complete Voice Pipeline

### Flow Diagram

```
1. User speaks wake word
   ↓
2. Wake-Word Service detects → confidence > 0.5
   ↓
3. Play beep (wake-word detected)
   ↓
4. Start recording audio (5-10 seconds)
   ↓
5. Send audio to AI Gateway /voice endpoint
   ↓
6. AI Gateway transcribes with Whisper
   ↓
7. Transcription sent to Ollama for intent
   ↓
8. Ollama returns JSON action plan
   ↓
9. AI Gateway executes Home Assistant service
   ↓
10. Response sent back to Wake-Word Service
   ↓
11. Play confirmation beep
```

## Docker Service Configuration

### Wake-Word Service Container

```yaml
wake-word:
  build:
    context: ./wake-word-service
    dockerfile: Dockerfile
  container_name: wake-word
  devices:
    - /dev/snd:/dev/snd  # Audio device passthrough
  environment:
    - AUDIO_DEVICE=hw:2,0
    - CHANNELS=6
    - SAMPLE_RATE=16000
    - WAKE_WORD_MODEL=hey_jarvis_v0.1
    - DETECTION_THRESHOLD=0.5
    - AI_GATEWAY_URL=http://host.docker.internal:8080
    - LOG_LEVEL=INFO
  depends_on:
    - ai-gateway
  restart: unless-stopped
  extra_hosts:
    - "host.docker.internal:host-gateway"
  volumes:
    - ./wake-word-service/models:/app/models:ro
    - ./wake-word-service/sounds:/app/sounds:ro
```

## File Structure

```
home-assistant-green/
├── wake-word-service/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py              # Main wake-word detection loop
│   │   ├── detector.py          # OpenWakeWord wrapper
│   │   ├── audio_capture.py     # PyAudio interface
│   │   ├── ai_gateway_client.py # HTTP client for AI Gateway
│   │   └── feedback.py          # Audio/LED feedback
│   ├── models/
│   │   └── hey_jarvis_v0.1.tflite  # Pre-trained wake-word model
│   └── sounds/
│       ├── beep.wav             # Wake-word detected
│       ├── listening.wav        # Now listening
│       └── success.wav          # Command executed
├── ai-gateway/
│   ├── app/
│   │   ├── routers/
│   │   │   ├── gateway.py       # Existing /ask endpoint
│   │   │   └── voice.py         # NEW: /voice endpoint for audio
│   │   └── services/
│   │       └── transcription.py # NEW: Whisper transcription
│   └── docker-compose.yml       # Updated with wake-word service
```

## Performance Metrics (Raspberry Pi 5)

### Resource Usage (Estimated)
- **CPU**: ~12% constant (1 core)
  - OpenWakeWord: ~5-10%
  - Audio capture: ~2%
- **RAM**: ~150-200 MB
  - OpenWakeWord model: ~50-100 MB
  - Python runtime: ~100 MB

### Latency Breakdown
- **Wake-word detection**: 100-300ms
- **Audio recording**: 5-10 seconds
- **Transcription** (Whisper tiny): 1-3 seconds
- **Ollama processing**: 0.5-1 second
- **Total response time**: 7-15 seconds

## Available Wake Words

### Pre-trained OpenWakeWord Models
- `hey_jarvis` ✅ (recommended - clear, distinct)
- `alexa`
- `hey_mycroft`
- `hey_rhasspy`

### Custom Wake Words (requires training)
- "Hey Assistant"
- "Computer"
- "OK Home"

## Audio Feedback System

### Beep Sounds
- **Wake detected**: Short beep (200ms)
- **Listening**: Rising tone (500ms)
- **Success**: Double beep (300ms)
- **Error**: Low buzz (400ms)

### LED Feedback (Optional - ReSpeaker has 12 RGB LEDs)
- **Idle**: Off
- **Wake detected**: Blue pulse
- **Listening**: Yellow animation
- **Processing**: Purple pulse
- **Success**: Green flash
- **Error**: Red flash

## AI Gateway Extensions

### New Endpoint: `/voice`

```python
@app.post("/voice")
async def process_voice(audio: UploadFile):
    # 1. Transcribe audio with Whisper
    transcription = await transcribe_audio(audio)

    # 2. Send to Ollama for intent
    plan = await translate_to_plan(transcription)

    # 3. Execute Home Assistant action
    result = await execute_ha_action(plan)

    return {
        "transcription": transcription,
        "plan": plan,
        "result": result
    }
```

### Whisper Integration
- **Model**: `whisper-tiny` (fastest, Raspberry Pi compatible)
- **Library**: `faster-whisper` (optimized for CPU)
- **Languages**: English + Polish support

## Security Considerations

- **Local Processing**: All audio stays on device
- **No Cloud**: Zero external API calls
- **Privacy**: No audio uploaded to cloud services
- **Sandboxed**: Docker containers isolated
- **Audio Permissions**: Only wake-word service has mic access

## Implementation Phases

### Phase 1: Wake-Word Detection (Current)
1. ✅ Verify microphone hardware
2. 🔲 Create wake-word Docker service
3. 🔲 Implement OpenWakeWord detection
4. 🔲 Test standalone wake-word detection

### Phase 2: Audio Transcription
1. 🔲 Add Whisper to AI Gateway
2. 🔲 Create `/voice` endpoint
3. 🔲 Test audio transcription

### Phase 3: Integration
1. 🔲 Connect wake-word to AI Gateway
2. 🔲 Implement full voice pipeline
3. 🔲 Add audio feedback
4. 🔲 Test end-to-end flow

### Phase 4: Optimization
1. 🔲 Tune detection threshold
2. 🔲 Optimize latency
3. 🔲 Add LED feedback
4. 🔲 Error handling and recovery

## Troubleshooting

### Common Issues

**Wake-word not detecting:**
- Check microphone levels: `arecord -D hw:2,0 -r 16000 -f S16_LE -c 6 -d 3 test.wav`
- Lower detection threshold (try 0.3)
- Verify model file loaded correctly

**High false positive rate:**
- Increase detection threshold (try 0.6-0.7)
- Check for background noise
- Ensure proper microphone placement

**Audio device not accessible in Docker:**
- Verify `/dev/snd` passthrough in docker-compose
- Check user/container in `audio` group
- Ensure no other service using microphone

## Future Enhancements

- **Multi-language support**: Detect language and switch models
- **Custom wake-word training**: Train on your voice
- **Noise cancellation**: Use all 4 microphones for beamforming
- **Continuous conversation**: Keep listening after wake-word
- **Voice profiles**: Recognize different users
- **Offline TTS**: Text-to-speech responses

## References

- **OpenWakeWord**: https://github.com/dscripka/openWakeWord
- **ReSpeaker Docs**: https://wiki.seeedstudio.com/ReSpeaker_4_Mic_Array/
- **Whisper**: https://github.com/openai/whisper
- **faster-whisper**: https://github.com/guillaumekln/faster-whisper
