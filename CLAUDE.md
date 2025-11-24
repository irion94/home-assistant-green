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
- ✅ **Audio Transcription (Vosk - offline speech-to-text)**
- ✅ **Conversation Mode (multi-turn dialogue with interrupt support)**
- ✅ **TTS Response (Coqui TTS local playback via ReSpeaker)**
- ✅ **Display Notifications (transcriptions shown on Nest Hub)**
- ✅ **LLM Function Calling (OpenAI tools for web search, device control, sensors)**
- ✅ **Web Search Integration (Brave Search API)**
- ✅ **TTS Text Normalization (units like °C, km/h spoken correctly)**
- ✅ **React Dashboard (browser-based voice interface with Web Speech API)**
- ✅ **Browser STT/TTS (Web Speech API for local speech recognition & synthesis)**

**Missing Components:**
- ❌ Custom wake-word model (Rico - needs retraining)
- ❌ Streaming with Function Calling (`/voice/stream` endpoint)

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
- `ai-gateway/app/main.py` — FastAPI application entry point
- `ai-gateway/app/routers/gateway.py` — `/ask`, `/conversation`, `/conversation/voice` endpoints
- `ai-gateway/app/services/ollama_client.py` — Ollama LLM integration
- `ai-gateway/app/services/ha_client.py` — Home Assistant API client
- `ai-gateway/app/services/intent_matcher.py` — Pattern matching for commands
- `ai-gateway/app/services/conversation_client.py` — Conversation state management with function calling
- `ai-gateway/app/services/llm_tools.py` — LLM tool definitions (web_search, control_light, get_home_data, get_time)
- `ai-gateway/app/services/web_search.py` — Brave Search API client
- `ai-gateway/docker-compose.yml` — Service orchestration (HA, MQTT, AI Gateway, Wake-word)
- `wake-word-service/app/main.py` — Wake-word detection loop with conversation mode
- `wake-word-service/app/detector.py` — OpenWakeWord TFLite/ONNX detection
- `wake-word-service/app/tts_service.py` — TTS with text normalization for units
- `wake-word-service/app/ai_gateway_client.py` — HTTP client for AI Gateway
- `react-dashboard/src/pages/VoiceAssistant.tsx` — Voice interface with Web Speech API STT/TTS
- `react-dashboard/src/api/gatewayClient.ts` — AI Gateway API client
- `react-dashboard/src/api/haWebSocket.ts` — Home Assistant WebSocket client
- `react-dashboard/src/types/api.ts` — API response types

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

### Phase 4: Integration 🔲 (Planned)

**Objective**: Connect all components into unified system

**Integration Flow**:
1. User speaks wake word
2. Voice module detects → triggers AI Gateway
3. AI Gateway captures audio → transcribes (Whisper/Vosk)
4. Transcription → Ollama for intent extraction
5. Ollama returns JSON plan → AI Gateway executes HA service
6. Home Assistant performs action
7. State update → Display UI reflects change
8. Audio/visual feedback to user

**Docker Orchestration**:
- Unified `docker-compose.yml` in project root
- All services with proper dependencies (`depends_on`)
- Shared network for inter-service communication
- Persistent volumes on SSD:
  - `/mnt/ssd/ha-config` → Home Assistant config
  - `/mnt/ssd/ollama-models` → Ollama model storage
  - `/mnt/ssd/mqtt-data` → MQTT persistence

### Phase 5: Production Hardening 🔲 (Planned)

**Objective**: Make system reliable and production-ready

**Components**:
- Auto-recovery on failures (restart policies)
- Centralized logging (Loki/Grafana or simple journald)
- Monitoring (Prometheus + HA integrations)
- Backup strategy:
  - Daily HA backups
  - Ollama model snapshots
  - Configuration backups to Git
- Documentation:
  - Setup guide
  - Troubleshooting playbook
  - Architecture diagrams

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
    ├── CLAUDE.md                       # Repository-specific Claude guide
    ├── ai-gateway/                     # AI Gateway subproject
    │   ├── docker-compose.yml          # HA + MQTT + AI Gateway orchestration
    │   ├── Dockerfile                  # AI Gateway container image
    │   ├── app/
    │   │   ├── main.py                 # FastAPI app entry point
    │   │   ├── routers/gateway.py      # /ask endpoint
    │   │   ├── services/
    │   │   │   ├── ollama_client.py    # Ollama LLM integration
    │   │   │   └── ha_client.py        # Home Assistant API client
    │   │   └── utils/
    │   └── tests/                      # AI Gateway tests
    ├── react-dashboard/                 # React voice dashboard
    │   ├── Dockerfile                  # Production container
    │   ├── src/
    │   │   ├── pages/
    │   │   │   ├── VoiceAssistant.tsx  # Voice UI with Web Speech API
    │   │   │   └── Dashboard.tsx       # Entity controls
    │   │   ├── api/
    │   │   │   ├── gatewayClient.ts    # AI Gateway client
    │   │   │   └── haWebSocket.ts      # HA WebSocket client
    │   │   └── types/                  # TypeScript definitions
    │   └── README.md                   # Setup documentation
    ├── wake-word-service/              # Wake-word detection service
    │   ├── Dockerfile                  # Service container
    │   ├── app/
    │   │   ├── main.py                 # Detection loop
    │   │   ├── detector.py             # OpenWakeWord
    │   │   └── tts_service.py          # TTS playback
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

## Next Steps

1. **Custom Wake-Word Training**:
   - Retrain "Rico" wake-word model with better parameters
   - Test ONNX vs TFLite performance
   - Adjust detection thresholds

2. **TTS Voice Improvement**:
   - Try different Coqui TTS models for more natural conversation
   - Consider XTTS v2 (requires more storage, moved Docker to SSD)
   - Test multi-language support (Polish/English)
   - Evaluate voice quality vs. performance trade-offs

3. **Conversation Mode Refinement**:
   - Fine-tune TTS wait time calculations
   - Improve interrupt detection accuracy
   - Test notify entity for different displays
   - Add visual feedback during processing

4. **Kiosk Display** 🚧:
   - ✅ Basic kiosk setup complete (systemd service, Chromium)
   - ⏳ Voice feedback panel (custom Lovelace card)
   - ⏳ AI Gateway SSE integration
   - ⏳ Touch screen calibration

5. **Production Hardening**:
   - Add monitoring/alerting
   - Implement backup strategy
   - Document troubleshooting procedures
   - Optimize resource usage

5. **Advanced Features**:
   - Context-aware responses (remember previous commands)
   - Proactive notifications
   - Multi-room audio support

6. **LLM Function Calling Enhancements**:
   - ✅ Basic function calling implemented (web_search, control_light, get_time, get_home_data)
   - ✅ Brave Search API integration
   - ⏳ Add streaming with function calling for `/voice/stream` endpoint
   - ⏳ Configure sensor entity mappings for `get_home_data` tool
   - Future: Add more tools (climate control, media playback, calendar)

7. **Streaming with Function Calling** (Phase 11):
   - Implement tool calling in `chat_stream_sentences` method
   - Handle tool calls within SSE streaming response
   - Allow LLM to decide tools in `/voice/stream` endpoint
   - This enables natural tool usage in all voice interactions

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
