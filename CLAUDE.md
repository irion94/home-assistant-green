# Home Assistant AI Companion Device - Development Guide

This file provides guidance for Claude Code when working on the Raspberry Pi 5 AI companion device project.

## Project Goal

Build a **Home Assistant-powered AI companion device** on Raspberry Pi 5 that combines:
- **Home Assistant** (automation hub) running in Docker
- **Ollama** (local LLM backend for AI processing)
- **AI Gateway** (FastAPI bridge connecting Ollama ↔ Home Assistant)
- **Voice wake-word detection** (planned)
- **Kiosk display interface** (planned)

All services run via Docker with persistent SSD storage.

## Current Project Status

**Location**: `/mnt/data-ssd/home-assistant-green/` (symlinked to `~/home-assistant-green`)

**Existing & Operational:**
- ✅ Home Assistant (Docker-based, GitOps workflow)
- ✅ AI Gateway (FastAPI app in `ai-gateway/` connecting Ollama ↔ Home Assistant)
- ✅ MQTT Broker (Mosquitto for IoT device communication)
- ✅ Comprehensive CI/CD pipeline (validation, testing, deployment)
- ✅ Custom components (Strava Coach, Daikin, Solarman, etc.)
- ✅ **Wake-Word Detection (OpenWakeWord - "Hey Jarvis", 90-98% accuracy)**
- ✅ **Audio Recording (7 seconds after wake-word)**
- ✅ **Audio Transcription (Vosk - offline speech-to-text, Whisper fallback)**
- ✅ **Conversation Mode (multi-turn dialogue with interrupt support)**
- ✅ **TTS Response (Coqui TTS local playback via ReSpeaker)**
- ✅ **Display Notifications (transcriptions shown on Nest Hub)**
- ✅ **LLM Function Calling (OpenAI tools for web search, device control, sensors)**
- ✅ **Web Search Integration (Brave Search API)**
- ✅ **TTS Text Normalization (units like °C, km/h spoken correctly)**
- ✅ **React Dashboard (browser-based voice interface with MQTT integration)**
- ✅ **Zustand State Management (centralized voice state, eliminates race conditions)**
- ✅ **Streaming TTS (sentence-by-sentence SSE for reduced latency)**
- ✅ **Dynamic Entity Discovery (AI semantic matching for HA entities)**
- ✅ **Advanced Entity Control (brightness, color, ambient moods)**
- ✅ **Fallback Pipeline (Vosk→Whisper STT, Pattern→LLM intent, VITS→XTTS TTS)**
- ✅ **Technical Debt Refactoring (consolidated entities, split routers, improved tests)**
- ✅ **Streaming STT (real-time interim transcripts, 0.5-1s first feedback, confidence-based Whisper fallback)**
- ✅ **Enhanced STT Accuracy (comprehensive Polish vocabulary hints, configurable confidence threshold)**
- ✅ **Conversation Streaming with Function Calling (LLM tools execute during voice interactions)**
- ✅ **Multi-Entity Light Control (all 7 lights controlled via "all lights" command)**

**Missing Components:**
- ❌ Custom wake-word model (Rico - needs retraining)
- ❌ Dedicated Kiosk Display (currently using Nest Hub as interim)

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Voice Input Methods                               │
├─────────────────────────────────┬───────────────────────────────────────────┤
│   Wake-Word Service (RPi)       │     React Dashboard (Browser)             │
│   - OpenWakeWord detection      │     - Web Speech API (local STT)          │
│   - Vosk transcription          │     - Web Speech Synthesis (local TTS)    │
│   - Always-on, hands-free       │     - Interactive UI with messages        │
└─────────────┬───────────────────┴───────────────┬───────────────────────────┘
              │                                   │
              ▼                                   ▼
        ┌─────────────────────────────────────────────┐
        │              AI Gateway (FastAPI)           │
        │   - /conversation endpoint (text)           │
        │   - /conversation/voice endpoint (audio)    │
        │   - LLM function calling (tools)            │
        └─────────────────┬───────────────────────────┘
                          │
                          ▼
              ┌─────────────────────────┐
              │   Ollama/OpenAI LLM     │
              │   - Intent extraction   │
              │   - Tool selection      │
              └───────────┬─────────────┘
                          │
                          ▼
              ┌─────────────────────────┐
              │    Home Assistant       │
              │   - Device control      │
              │   - TTS to Nest Hub     │
              │   - State updates       │
              └─────────────────────────┘
```

### Current Implementation

**AI Gateway** (`home-assistant-green/ai-gateway/`):
- FastAPI application bridging Ollama and Home Assistant
- Natural language command processing (English/Polish)
- Translates user intent → structured JSON → HA service calls
- Docker-based deployment with health checks

**React Dashboard** (`home-assistant-green/react-dashboard/`):
- Vite + React + TypeScript application
- Web Speech API for browser-based STT (no audio transfer)
- Web Speech Synthesis for local TTS
- Real-time entity state updates via Home Assistant WebSocket
- Kiosk-optimized UI for touch interaction

**Docker Compose** (`home-assistant-green/ai-gateway/docker-compose.yml`):
- Home Assistant container (port 8123)
- MQTT Broker (Mosquitto, ports 1883/9001)
- AI Gateway (port 8080)
- React Dashboard (port 3000)
- PostgreSQL with pgvector (port 5432)
- Wake-word service
- Ollama runs on host, accessed via `host.docker.internal:11434`

**Key Files:**

*AI Gateway:*
- `ai-gateway/app/main.py` — FastAPI application entry point
- `ai-gateway/app/routers/ask.py` — `/ask` endpoint
- `ai-gateway/app/routers/voice.py` — `/voice`, `/voice/stream` SSE endpoints
- `ai-gateway/app/routers/conversation.py` — `/conversation` endpoints
- `ai-gateway/app/services/ollama_client.py` — Ollama LLM integration
- `ai-gateway/app/services/openai_client.py` — OpenAI API integration
- `ai-gateway/app/services/ha_client.py` — Home Assistant API client
- `ai-gateway/app/services/intent_matcher.py` — Pattern matching for commands
- `ai-gateway/app/services/conversation_client.py` — Conversation state + function calling
- `ai-gateway/app/services/entity_discovery.py` — Dynamic HA entity discovery
- `ai-gateway/app/services/entities.py` — Centralized entity mappings (single source of truth)
- `ai-gateway/app/services/llm_tools.py` — LLM tool definitions
- `ai-gateway/app/services/web_search.py` — Brave Search API client
- `ai-gateway/app/services/pipeline/executor.py` — Intent pipeline execution
- `ai-gateway/app/services/pipeline/stt_pipeline.py` — Vosk→Whisper STT cascade
- `ai-gateway/docker-compose.yml` — Service orchestration

*Wake-Word Service:*
- `wake-word-service/app/main.py` — Detection loop + conversation mode + streaming STT
- `wake-word-service/app/detector.py` — OpenWakeWord TFLite/ONNX detection
- `wake-word-service/app/streaming_transcriber.py` — Vosk streaming STT with interim results
- `wake-word-service/app/tts_service.py` — TTS with text normalization
- `wake-word-service/app/audio_capture.py` — Audio recording with VAD + streaming callback
- `wake-word-service/app/feedback.py` — LED feedback states

*React Dashboard:*
- `react-dashboard/src/stores/voiceStore.ts` — Zustand state management
- `react-dashboard/src/services/mqttService.ts` — MQTT client with Zustand integration
- `react-dashboard/src/components/kiosk/VoiceOverlay.tsx` — Voice interaction overlay
- `react-dashboard/src/components/kiosk/KioskHome.tsx` — Kiosk main view
- `react-dashboard/src/api/gatewayClient.ts` — AI Gateway API client
- `react-dashboard/src/api/haWebSocket.ts` — Home Assistant WebSocket client

*Documentation:*
- `docs/FALLBACK_PIPELINE.md` — Detailed pipeline architecture and phases

## Development Phases

### Phase 1: Docker Foundation ✅ (Mostly Complete)

**Status**: Operational
- Home Assistant container configured
- Ollama running on host (or can be containerized)
- AI Gateway bridges Ollama ↔ Home Assistant
- MQTT broker for IoT devices

**Next Steps**:
- Verify Ollama installation and model availability
- Test AI Gateway functionality
- Ensure all services start on boot

### Phase 2: Voice Wake-Word Module ✅ (COMPLETE)

**Status**: Fully operational with conversation mode

**Technology Used**:
- OpenWakeWord (TFLite inference)
- Vosk (offline speech-to-text)
- Google Translate TTS (via Home Assistant)

**Implementation Details**:
- Wake-word: "Hey Jarvis"
- Microphone: ReSpeaker 4 Mic Array (UAC1.0)
- Audio: 16kHz, 2-channel → mono
- Container: `wake-word` service in Docker Compose
- Models stored on SSD: `/mnt/data-ssd/ha-data/wake-word-models/`
- Detection threshold: 0.35 (35% confidence)

**What's Working**:
- ✅ Audio capture from ReSpeaker microphone
- ✅ Wake-word detection (OpenWakeWord TFLite models)
- ✅ 7-second audio recording after detection
- ✅ HTTP POST to AI Gateway with recorded audio
- ✅ Docker container with audio device passthrough
- ✅ Auto-restart on failure
- ✅ Persistent model storage
- ✅ **Vosk transcription (offline, Polish/English)**
- ✅ **Conversation mode (multi-turn dialogue)**
- ✅ **TTS response via Nest Hub (1.2x speed)**
- ✅ **Language detection (Polish/English auto-switch)**
- ✅ **Interrupt detection ("przerwij", "stop", etc.)**
- ✅ **Display transcriptions on Nest Hub**

**Conversation Mode Features**:
- Triggered by phrases like "porozmawiajmy", "let's talk"
- Multi-turn dialogue until "zakończ", "kończymy", "bye"
- Shows transcribed text on Nest Hub display
- Faster TTS playback (1.2x speed)
- Interrupt support during AI response

**Key Files**:
- `wake-word-service/app/main.py` — Main loop with conversation mode
- `wake-word-service/app/detector.py` — Wake-word detection
- `wake-word-service/app/audio_capture.py` — Audio recording with VAD
- `wake-word-service/app/ai_gateway_client.py` — API client with stop_media()
- `ai-gateway/app/services/conversation_client.py` — Conversation state management

**Known Issues**:
- Audio feedback beeps fail (no audio output in container)
- Custom "Rico" wake-word needs retraining (low accuracy)

**Progress Doc**: `docs/WAKE_WORD_PROGRESS.md`

### Phase 3: Kiosk Display UI ✅ (COMPLETE)

**Objective**: Display Home Assistant dashboards and voice interaction feedback

**Status**: React Dashboard fully operational with voice control

**Technology**: React + Vite + TypeScript + Web Speech API

**Two Interface Options**:

1. **React Dashboard** (Primary - Browser-based):
   - Modern touch-optimized UI
   - Web Speech API for local STT (no audio transfer)
   - Web Speech Synthesis for TTS responses
   - Real-time entity state via WebSocket
   - Voice Assistant with conversation history
   - Light/climate/sensor controls

2. **Chromium Kiosk Mode** (Alternative - HA Lovelace):
   - Systemd service for auto-start
   - Displays HA dashboards directly

**Key Files**:
- `react-dashboard/src/pages/VoiceAssistant.tsx` — Voice interface with STT/TTS
- `react-dashboard/src/pages/Dashboard.tsx` — Entity controls
- `react-dashboard/src/api/gateway.ts` — AI Gateway client
- `react-dashboard/src/api/homeAssistant.ts` — HA WebSocket client
- `kiosk-service/kiosk.service` — Systemd unit file (alternative)

**What's Working**:
- ✅ React Dashboard with voice assistant
- ✅ Web Speech API STT (local speech recognition)
- ✅ Web Speech Synthesis TTS (speaks responses)
- ✅ Real-time entity state updates
- ✅ Touch-optimized kiosk UI
- ✅ Conversation message history
- ✅ Polish/English language support
- ✅ Docker deployment (port 3000)

**Voice Assistant Features**:
- Tap microphone to speak or type commands
- Shows interim transcription while speaking
- Displays conversation as chat bubbles
- Speaks AI responses automatically
- Toggle TTS on/off
- Stop speaking with volume button

### Phase 4: Integration ✅ (COMPLETE)

**Objective**: Connect all components into unified system

**What's Working**:
- ✅ Wake-word triggers AI Gateway via HTTP
- ✅ Vosk→Whisper STT cascade with confidence thresholds
- ✅ Pattern→LLM intent pipeline with fallback to AI conversation
- ✅ Home Assistant service execution
- ✅ MQTT-based state sync between services
- ✅ React Dashboard with Zustand state management
- ✅ Streaming TTS (sentence-by-sentence SSE)

**Docker Orchestration** (`ai-gateway/docker-compose.yml`):
- All services with proper dependencies (`depends_on`)
- Shared network for inter-service communication
- Persistent volumes on SSD
- Health checks for all services

### Phase 5: Voice UX Refinement ✅ (COMPLETE)

**Objective**: Improve voice interaction user experience

**What's Working**:
- ✅ Zustand state management (eliminates callback race conditions)
- ✅ MQTT topic structure: `voice_assistant/room/{room_id}/...`
- ✅ Conversation mode via voice ("porozmawiajmy") or UI button
- ✅ Orange animated conversation mode indicator
- ✅ Auto-overlay on wake-word detection
- ✅ Session-based message history

### Phase 6-8: Advanced Features ✅ (COMPLETE)

**Phase 6 - Streaming TTS**:
- ✅ SSE endpoint `/voice/stream` for sentence-by-sentence streaming
- ✅ TTS queue management with interrupt support
- ✅ Reduced first-word latency (2-4s → 0.5-1s)

**Phase 7 - Dynamic Entity Discovery**:
- ✅ Automatic entity mapping using AI semantic matching
- ✅ No manual entity configuration required
- ✅ LLM caching + pattern auto-learning
- ✅ Brightness, color (RGB, kelvin), transition control
- ✅ Ambient mood creation ("romantyczny klimat", "tryb kino")
- ✅ Multi-action scene execution
- ✅ Polish color name mapping

**Phase 8 - Streaming STT**:
- ✅ Real-time interim transcripts via Vosk streaming API
- ✅ MQTT topics: `transcript/interim`, `transcript/final`, `transcript/refined`
- ✅ Confidence-based Whisper fallback (< 70% threshold)
- ✅ Reduced perceived latency: 8-13s → 0.5-1s for first feedback
- ✅ Debug Panel integration for interim results
- ✅ Feature flag for easy rollback (`STREAMING_STT_ENABLED`)
- ✅ `StreamingTranscriber` class with `process_chunk()` and `finalize()`
- ✅ `record_streaming()` method with per-chunk callbacks
- ✅ Sequence tracking for interim result ordering
- ✅ 70% CPU savings when Whisper refinement not needed

**Documentation**: `docs/STREAMING_STT.md`

### Phase 9: Streaming Response Integration ✅ (COMPLETE)

**Objective**: Token-by-token streaming responses integrated with VoiceOverlay via MQTT

**Implementation**:
- ✅ Backend streaming client (`send_conversation_stream()` in wake-word service)
- ✅ Zustand streaming state management (`isStreaming`, `streamingContent`, etc.)
- ✅ MQTT streaming topics: `response/stream/start`, `response/stream/chunk`, `response/stream/complete`
- ✅ VoiceOverlay UI with blinking cursor and streaming indicator
- ✅ Removed legacy response publishing to prevent duplicate messages
- ✅ Auto-close delay during streaming to prevent premature overlay closure

**Architecture**:
```
Wake-word service → AI Gateway /conversation/stream (SSE)
     ↓
Token-by-token callback → Publish to MQTT topics
     ↓
React Dashboard MQTT handlers → Zustand store updates
     ↓
VoiceOverlay renders streaming message with blinking cursor
```

**What's Working**:
- Token-by-token streaming with 0.5-1s first token latency
- Real-time UI updates via MQTT pub/sub
- Blinking cursor visual feedback during streaming
- Single message bubble (no duplicates)
- Overlay stays open until streaming completes

**Key Files**:
- `wake-word-service/app/ai_gateway_client.py` — Async streaming client
- `wake-word-service/app/main.py` — Streaming integration in `process_interaction()`
- `react-dashboard/src/stores/voiceStore.ts` — Streaming state management
- `react-dashboard/src/services/mqttService.ts` — MQTT streaming handlers
- `react-dashboard/src/components/kiosk/VoiceOverlay.tsx` — Streaming UI

### Phase 10: Technical Debt ✅ (COMPLETE)

- ✅ Consolidated entity mappings (`entities.py`)
- ✅ Split `gateway.py` into modular routers
- ✅ Created `.env.example` template
- ✅ Improved test coverage (intent_matcher, llm_tools, web_search)
- ✅ Docker security improvements (capabilities vs privileged)
- ⚠️ Manual: Rotate exposed API keys

### Phase 11: STT Enhancements & Function Calling ✅ (COMPLETE)

**Objective**: Improve STT accuracy and enable function calling in conversation streaming

**What's Working**:
- ✅ Enhanced Whisper vocabulary hints (comprehensive Polish home automation phrases)
- ✅ Configurable STT confidence threshold (environment variable `STT_CONFIDENCE_THRESHOLD`)
- ✅ Word boundary matching for end command detection (fixes false positives like "pa" in "sypialni")
- ✅ Function calling in `/conversation/stream` endpoint (LLM can execute tools during streaming)
- ✅ Multi-entity light control (all 7 lights controlled when room="all")

**Key Files Updated**:
- `ai-gateway/app/services/whisper_client.py` - Enhanced vocabulary hints
- `ai-gateway/app/services/conversation_client.py` - Tool calling in both `chat_stream()` and `chat_stream_sentences()`
- `ai-gateway/app/services/llm_tools.py` - Fixed "all lights" to control 7 individual entities
- `wake-word-service/app/main.py` - Word boundary regex for end command detection

### Phase 12: Dedicated Kiosk Display 🔲 (PLANNED)

**Objective**: Replace Nest Hub with dedicated RPi display

- 🔲 Chromium kiosk mode on RPi5
- 🔲 Custom Lovelace voice feedback card
- 🔲 SSE integration for real-time updates
- 🔲 Touch screen support

See `docs/FALLBACK_PIPELINE.md` for detailed implementation notes.

## AI Assistant Operation Rules

When working on this project, follow these principles:

### 1. Think Modularly

Build step-by-step: Docker base → HA → Ollama → Voice → Display

For each stage:
- Propose architecture before implementation
- Create/modify configuration files incrementally
- Update documentation alongside code changes
- Test each module independently before integration

### 2. Focus on Maintainability

Optimize for Raspberry Pi 5 deployment:
- Pin Docker image versions for reproducibility
- Use persistent SSD-backed volumes (avoid SD card writes)
- Design for easy updates and backups (especially HA + Ollama models)
- Keep resource usage low (memory, CPU)

### 3. Home Assistant Integration

All AI features must integrate with Home Assistant:
- Ollama communicates via AI Gateway (HTTP/gRPC)
- AI Gateway executes HA service calls via REST API
- Voice module triggers HA events
- Display UI reflects HA state changes
- Automations can trigger AI processing

### 4. Code Workflow

Before modifying anything:
1. Analyze existing files (especially `home-assistant-green/` repo)
2. Create TODO plan using TodoWrite tool
3. Perform edits incrementally
4. Test at each step
5. Avoid overly complex designs — prioritize simple, reproducible setups

### 5. Communication Style

- Respond concisely but precisely
- When information is missing (file/data), clearly state requirements
- After major actions, propose:
  - Next possible steps
  - Verification/tests (Docker commands, HA logs, Ollama endpoints)

## Common Commands

### Docker Operations

```bash
# Navigate to project
cd ~/home-assistant-green/ai-gateway

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service health
docker-compose ps
curl http://localhost:8080/health

# Restart specific service
docker-compose restart ai-gateway

# Stop all services
docker-compose down
```

### Ollama Operations

```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# List installed models
ollama list

# Pull new model (recommended for RPi5: llama3.2:3b)
ollama pull llama3.2:3b

# Test Ollama directly
ollama run llama3.2:3b "Turn on living room lights"
```

### Home Assistant

```bash
# Check HA API
curl http://localhost:8123/api/

# Test HA service call (requires token)
curl -X POST http://localhost:8123/api/services/light/turn_on \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"entity_id": "light.living_room"}'
```

### AI Gateway Testing

```bash
# Test natural language command
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"text": "Turn on living room lights"}'

# Polish command
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"text": "Włącz światło w salonie"}'

# Test conversation mode (text)
curl -X POST http://localhost:8080/conversation \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the weather like?", "session_id": "test123"}'

# Test conversation voice endpoint (with audio file)
curl -X POST http://localhost:8080/conversation/voice \
  -F "audio=@recording.wav" \
  -F "session_id=test123"

# Check health
curl http://localhost:8080/health
```

### Wake-Word Service

```bash
# View wake-word logs
docker-compose logs -f wake-word

# Restart wake-word service
docker-compose restart wake-word

# Check current configuration
docker-compose exec wake-word env | grep -E "WAKE_WORD|THRESHOLD|FRAMEWORK"

# Check streaming STT status
docker-compose logs wake-word | grep "Streaming STT"
# Should see: "Streaming STT initialized (Vosk, confidence threshold: 0.7)"

# Monitor interim transcripts via MQTT
docker-compose exec mosquitto mosquitto_sub -t "voice_assistant/room/+/session/+/transcript/#" -v

# Disable streaming STT (rollback to batch mode)
# In docker-compose.yml, add: STREAMING_STT_ENABLED=false
# Then: docker-compose restart wake-word

# Adjust STT confidence threshold (AI Gateway)
# Controls when Vosk triggers Whisper fallback (0.0-1.0)
# Lower = more Whisper (slower, more accurate), Higher = more Vosk (faster)
# In docker-compose.yml: STT_CONFIDENCE_THRESHOLD=0.6
# Then: docker-compose restart ai-gateway

# Adjust streaming STT confidence threshold (Wake-Word Service)
# In docker-compose.yml: STREAMING_STT_CONFIDENCE_THRESHOLD=0.6
# Then: docker-compose restart wake-word
```

### React Dashboard

```bash
# Access React Dashboard
open http://localhost:3000

# View dashboard logs
docker compose logs -f react-dashboard

# Rebuild after changes
docker compose build react-dashboard && docker compose up -d react-dashboard

# Check health
curl -s http://localhost:3000/health

# Development mode (outside Docker)
cd ~/home-assistant-green/react-dashboard
npm install
npm run dev
```

## File Structure

```
/home/irion94/
├── CLAUDE.md                           # This file
└── home-assistant-green -> /mnt/data-ssd/home-assistant-green  # Symlink to SSD

/mnt/data-ssd/
├── home-assistant-green/               # Main repository (on SSD)
    ├── README.md                       # Repository documentation
    ├── ai-gateway/                     # AI Gateway subproject
    │   ├── docker-compose.yml          # HA + MQTT + AI Gateway + Wake-word orchestration
    │   ├── Dockerfile                  # AI Gateway container image
    │   ├── .env.example                # Environment template
    │   ├── app/
    │   │   ├── main.py                 # FastAPI app entry point
    │   │   ├── models.py               # Pydantic models + Config
    │   │   ├── routers/
    │   │   │   ├── ask.py              # /ask endpoint
    │   │   │   ├── voice.py            # /voice, /voice/stream endpoints
    │   │   │   ├── conversation.py     # /conversation endpoints
    │   │   │   └── dependencies.py     # Shared FastAPI dependencies
    │   │   ├── services/
    │   │   │   ├── ollama_client.py    # Ollama LLM integration
    │   │   │   ├── openai_client.py    # OpenAI API integration
    │   │   │   ├── ha_client.py        # Home Assistant API client
    │   │   │   ├── intent_matcher.py   # Pattern matching
    │   │   │   ├── conversation_client.py  # Conversation + function calling
    │   │   │   ├── entity_discovery.py # Dynamic entity discovery
    │   │   │   ├── entities.py         # Centralized entity mappings
    │   │   │   ├── llm_tools.py        # LLM tool definitions
    │   │   │   ├── web_search.py       # Brave Search client
    │   │   │   └── pipeline/
    │   │   │       ├── executor.py     # Intent pipeline
    │   │   │       └── stt_pipeline.py # STT cascade
    │   │   └── utils/
    │   │       └── text.py             # Language detection, formatting
    │   ├── tests/                      # AI Gateway tests
    │   └── docs/
    │       └── FALLBACK_PIPELINE.md    # Pipeline architecture
    ├── react-dashboard/                # React voice dashboard
    │   ├── Dockerfile                  # Production container
    │   ├── src/
    │   │   ├── stores/
    │   │   │   └── voiceStore.ts       # Zustand state management
    │   │   ├── services/
    │   │   │   └── mqttService.ts      # MQTT client
    │   │   ├── components/
    │   │   │   └── kiosk/
    │   │   │       ├── KioskHome.tsx   # Main kiosk view
    │   │   │       └── VoiceOverlay.tsx # Voice interaction UI
    │   │   ├── api/
    │   │   │   ├── gatewayClient.ts    # AI Gateway client
    │   │   │   └── haWebSocket.ts      # HA WebSocket client
    │   │   └── types/                  # TypeScript definitions
    │   └── README.md                   # Setup documentation
    ├── wake-word-service/              # Wake-word detection service
    │   ├── Dockerfile                  # Service container
    │   ├── app/
    │   │   ├── main.py                 # Detection loop + conversation mode
    │   │   ├── detector.py             # OpenWakeWord detection
    │   │   ├── audio_capture.py        # Audio recording with VAD
    │   │   ├── tts_service.py          # TTS playback + normalization
    │   │   ├── feedback.py             # LED states
    │   │   └── ai_gateway_client.py    # HTTP client
    │   └── README.md                   # Setup documentation
    ├── kiosk-service/                  # Chromium kiosk (alternative)
    │   ├── kiosk.service               # Systemd unit file
    │   ├── install.sh                  # Installation script
    │   └── README.md                   # Setup documentation
    ├── config/                         # Home Assistant configuration
    │   ├── configuration.yaml
    │   ├── automations.yaml
    │   ├── packages/                   # Modular HA configs
    │   └── custom_components/          # Custom integrations
    ├── scripts/                        # Deployment/utility scripts
    └── docs/                           # Additional documentation
```

## Recent Updates (2025-11-26)

### STT Enhancements & Bug Fixes
- **Enhanced Whisper Vocabulary**: Added comprehensive Polish home automation vocabulary hints covering lights, climate, media, sensors, and conversation commands. Expected 15-25% improvement in domain-specific recognition.
- **Configurable STT Threshold**: Added `STT_CONFIDENCE_THRESHOLD` environment variable (default: 0.7) to tune Vosk→Whisper fallback behavior.
- **End Command Fix**: Fixed false positive detection where "pa" in words like "sypialni" (bedroom) was incorrectly triggering conversation end. Now uses word boundary regex matching.

### Function Calling in Conversation
- **Streaming Tool Execution**: LLM can now execute tools (control_light, web_search, etc.) during streaming conversations via `/conversation/stream` endpoint.
- **Dual Method Support**: Function calling implemented in both `chat_stream()` (token-by-token) and `chat_stream_sentences()` (sentence-by-sentence) methods.
- **Proper Error Handling**: Tool executor uses `.execute()` method correctly, with full error logging and recovery.

### Light Control Improvements
- **Multi-Entity Control**: "All lights" command now properly controls all 7 individual light entities instead of invalid "all" entity.
- **Correct API Usage**: Multi-entity commands now pass list in `data["entity_id"]` field per HA API conventions.

**Commits:**
- `0885cc9` feat: enhance Whisper vocabulary hints for Polish home automation
- `11cc091` feat: add configurable STT confidence threshold
- `a8b35aa` fix: use word boundary matching for end command detection
- `519bf8f` feat: add function calling support to conversation streaming
- `b0ed56c` fix: control all 7 lights when room="all" requested

## Next Steps

### Short-Term (Phase 12)

1. **Dedicated Kiosk Display**:
   - Configure Chromium kiosk on RPi5 with 7" touchscreen
   - Create custom Lovelace card for voice feedback
   - Integrate SSE streaming for real-time updates
   - Replace Nest Hub dependency

### Future Enhancements

3. **Custom Wake-Word**:
   - Retrain "Rico" model with better parameters
   - Test ONNX vs TFLite performance

4. **Multi-Room Support**:
   - Room-based entity discovery
   - Location-aware commands
   - Cross-room audio routing

5. **Additional LLM Tools**:
   - Climate control (set temperature, HVAC modes)
   - Media playback (Spotify, local media)
   - Calendar integration
   - Reminder/timer functionality

6. **Production Hardening**:
   - Monitoring/alerting (Prometheus + Grafana)
   - Automated backups
   - ⚠️ Rotate exposed API keys (HA_TOKEN, OPENAI_API_KEY, BRAVE_API_KEY)

## Important Considerations

### Security
- Never commit secrets (`.env` files, tokens)
- Use Home Assistant long-lived tokens (not admin passwords)
- Run on trusted network or behind reverse proxy

### Performance (Raspberry Pi 5)
- **Recommended Ollama models**:
  - `llama3.2:3b` — Best balance (2-3GB RAM, ~500ms-1s response)
  - `phi3:mini` — Faster, less accurate
  - Avoid 7B+ models (too slow for real-time voice)
- **Memory management**: Limit HA recorder history, prune logs
- **Storage**: Use SSD for all persistent volumes (SD card for boot only)

### Reliability
- Set Docker restart policies to `unless-stopped`
- Implement health checks for all services
- Monitor resource usage (RAM, CPU, disk)
- Regular backups of HA config and Ollama models

## Resources

- **Repository**: `/mnt/data-ssd/home-assistant-green/` (or `~/home-assistant-green` via symlink)
- **AI Gateway README**: `~/home-assistant-green/ai-gateway/README.md`
- **Repository README**: `~/home-assistant-green/README.md`
- **HA Documentation**: https://www.home-assistant.io/docs/
- **Ollama Documentation**: https://github.com/ollama/ollama
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
