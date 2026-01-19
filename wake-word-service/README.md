# Wake-Word Service

Standalone voice wake-word detection service with multi-platform support for Home Assistant AI companion devices.

## Features

- **Wake-word detection** using OpenWakeWord ("Hey Jarvis")
- **Speech-to-text** via Vosk (offline) with Whisper fallback
- **Text-to-speech** via Coqui TTS (VITS/XTTS v2)
- **Multi-platform support**: macOS (development), Linux, Raspberry Pi
- **Auto-detect microphones** with preference-based selection
- **LED feedback** via ReSpeaker pixel ring (RPi only)
- **MQTT integration** for React Dashboard communication
- **Conversation mode** for multi-turn dialogue

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Wake-Word Service                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ OpenWakeWord│  │    Vosk     │  │     Coqui TTS       │ │
│  │  Detection  │  │     STT     │  │  (VITS/XTTS v2)     │ │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
│         │                │                     │            │
│  ┌──────▼────────────────▼─────────────────────▼──────────┐│
│  │              Platform Abstraction Layer                ││
│  │  ┌────────────┐ ┌────────────┐ ┌────────────────────┐  ││
│  │  │  Audio In  │ │ Audio Out  │ │    LED Feedback    │  ││
│  │  │ (PyAudio)  │ │(ALSA/PyAudio)│ │(PixelRing/Console)│  ││
│  │  └────────────┘ └────────────┘ └────────────────────┘  ││
│  └────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
    ┌─────────┐                  ┌─────────────┐
    │   AI    │                  │    MQTT     │
    │ Gateway │                  │   Broker    │
    └─────────┘                  └─────────────┘
```

## Quick Start

### On Raspberry Pi (Production)

```bash
cd wake-word-service

# Copy and configure environment
cp .env.example .env
nano .env  # Set AI_GATEWAY_URL, MQTT_HOST, etc.

# Start with ALSA audio support
docker compose -f docker-compose.yml -f docker-compose.linux.yml up -d

# Or use the helper script
./run.sh rpi
```

### On Linux (Generic)

```bash
./run.sh linux
# or
docker compose -f docker-compose.yml -f docker-compose.linux.yml up -d
```

### On macOS (Development)

Note: Docker Desktop cannot access host microphone. Use for testing non-audio components only.

```bash
./run.sh macos
# or
docker compose up -d
```

## File Structure

```
wake-word-service/
├── docker-compose.yml          # Base compose (macOS safe, no /dev/snd)
├── docker-compose.linux.yml    # Linux/RPi override (ALSA devices)
├── Dockerfile                  # Multi-platform container image
├── .env.example                # Environment template
├── run.sh                      # Platform-aware launcher script
├── entrypoint.sh               # Platform detection & initialization
├── requirements.txt            # Python dependencies
├── sounds/                     # Audio feedback files
│   ├── wake_detected.wav
│   ├── listening.wav
│   ├── success.wav
│   └── error.wav
└── app/
    ├── main.py                 # Main detection loop + conversation mode
    ├── detector.py             # OpenWakeWord TFLite/ONNX detection
    ├── audio_capture.py        # Audio input with device auto-detection
    ├── streaming_transcriber.py # Vosk streaming STT
    ├── transcriber.py          # Batch STT
    ├── whisper_transcriber.py  # Whisper fallback STT
    ├── tts_service.py          # TTS with text normalization
    ├── tts_queue.py            # TTS queue management
    ├── ai_gateway_client.py    # AI Gateway HTTP client
    ├── feedback.py             # Audio/LED feedback (uses platform layer)
    ├── state_machine.py        # Voice interaction state machine
    ├── parallel_stt.py         # Parallel STT processing
    └── platforms/              # Platform abstraction layer
        ├── __init__.py         # Factory functions
        ├── detector.py         # Platform detection (macOS/Linux/RPi)
        ├── audio_backend.py    # Abstract audio input interface
        ├── audio_pyaudio.py    # PyAudio implementation (all platforms)
        ├── playback.py         # Abstract audio output interface
        ├── playback_alsa.py    # ALSA output (Linux only)
        ├── playback_pyaudio.py # PyAudio output (cross-platform)
        └── feedback_backend.py # LED/console feedback abstraction
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Platform (auto, macos, linux, rpi)
PLATFORM=auto

# Room identifier for multi-device support
ROOM_ID=living_room

# Audio input preferences (comma-separated, matched case-insensitive)
AUDIO_DEVICE_PREFERENCE=ReSpeaker,USB Audio,Built-in Microphone
AUDIO_DEVICE=hw:2,0              # Legacy ALSA device fallback
AUDIO_INPUT_CHANNELS=6           # ReSpeaker=6, most USB=1-2

# Audio output
AUDIO_OUTPUT_DEVICE=plughw:2,0   # ALSA output device
PLAYBACK_BACKEND=auto            # auto, alsa, pyaudio

# Wake-word detection
WAKE_WORD_MODEL=hey_jarvis
DETECTION_THRESHOLD=0.50
INFERENCE_FRAMEWORK=tflite       # tflite or onnx

# AI Gateway connection
AI_GATEWAY_URL=http://192.168.1.100:8080
REQUEST_TIMEOUT=120

# MQTT Broker
MQTT_HOST=192.168.1.100
MQTT_PORT=1883

# STT Configuration
VOSK_MODEL_PATH=/app/models/vosk/vosk-model-small-pl-0.22
STREAMING_STT_ENABLED=true
STREAMING_STT_CONFIDENCE_THRESHOLD=0.7

# TTS Configuration
TTS_HOME=/app/tts-cache

# Feedback
FEEDBACK_CONSOLE=false           # Enable emoji feedback (dev)
ENABLE_BEEP=true
BEEP_VOLUME=0.8

# Logging
LOG_LEVEL=INFO
```

## Platform Support

### Raspberry Pi (Full Features)

- ReSpeaker 4 Mic Array support
- Pixel ring LED feedback
- ALSA audio input/output
- USB device reset capability
- GPIO access for hardware control

```bash
# Required devices in docker-compose.linux.yml
devices:
  - /dev/snd:/dev/snd

# Capabilities
cap_add:
  - SYS_RAWIO   # GPIO access
  - IPC_LOCK    # Audio device locking
```

### Linux (Generic)

- ALSA audio input/output
- Auto-detect USB microphones
- No LED support (silent fallback)

### macOS (Development Only)

- PyAudio backend (no ALSA)
- **Docker cannot access host microphone**
- Use for testing non-audio components
- Console feedback available (`FEEDBACK_CONSOLE=true`)

## Audio Device Auto-Detection

The service searches for audio devices in this order:

1. **ReSpeaker** - Seeed ReSpeaker 4 Mic Array (RPi)
2. **Configured device** - Device matching `AUDIO_DEVICE` setting
3. **Built-in Microphone** - macOS built-in mic
4. **Any input device** - First available input device

Configure preferences via `AUDIO_DEVICE_PREFERENCE`:
```bash
AUDIO_DEVICE_PREFERENCE=ReSpeaker,USB Audio,Blue Yeti,Built-in
```

## Docker Compose Files

### docker-compose.yml (Base)

Safe for all platforms. Does not mount `/dev/snd`.

```yaml
services:
  wake-word:
    build: .
    container_name: wake-word
    environment:
      - PLATFORM=${PLATFORM:-auto}
      - AI_GATEWAY_URL=${AI_GATEWAY_URL:-http://host.docker.internal:8080}
      # ... other env vars
    volumes:
      - ./sounds:/app/sounds:ro
      - wake-word-models:/app/models
      - tts-cache:/app/tts-cache
```

### docker-compose.linux.yml (Linux/RPi Override)

Adds ALSA device access for Linux hosts:

```yaml
services:
  wake-word:
    devices:
      - /dev/snd:/dev/snd
    group_add:
      - audio
    cap_add:
      - SYS_RAWIO
      - IPC_LOCK
    security_opt:
      - seccomp:unconfined
```

## Helper Script (run.sh)

```bash
./run.sh              # Auto-detect platform
./run.sh macos        # Force macOS mode
./run.sh linux        # Force Linux mode
./run.sh rpi          # Force RPi mode

./run.sh down         # Stop service
./run.sh logs         # View logs
./run.sh build        # Rebuild image
./run.sh restart      # Restart service
```

## Volumes

| Volume | Path | Description |
|--------|------|-------------|
| `wake-word-models` | `/app/models` | Wake-word & Vosk models |
| `tts-cache` | `/app/tts-cache` | TTS model cache (~2GB) |

## Troubleshooting

### No audio devices found (macOS)

This is expected. Docker Desktop cannot access host audio hardware.

### ALSA errors on Linux

Ensure `/dev/snd` is mounted and user is in `audio` group:
```bash
docker compose -f docker-compose.yml -f docker-compose.linux.yml up -d
```

### ReSpeaker not detected

1. Check USB connection: `lsusb | grep -i seeed`
2. Check ALSA devices: `arecord -l`
3. Try USB reset: Container will attempt automatic reset on startup

### LED feedback not working

- LEDs only work on Raspberry Pi with ReSpeaker
- Requires `SYS_RAWIO` capability
- Check `/dev/spidev0.0` exists

### TTS models downloading slowly

First startup downloads ~2GB of TTS models. Use persistent volume:
```yaml
volumes:
  - tts-cache:/app/tts-cache
```

## Integration with AI Gateway

The service connects to AI Gateway for:
- Voice command processing (`/conversation/voice`)
- Streaming responses (`/conversation/stream`)
- Text-to-speech synthesis

Configure connection:
```bash
AI_GATEWAY_URL=http://192.168.1.100:8080
REQUEST_TIMEOUT=120
```

## MQTT Topics

The service publishes to these MQTT topics:

```
voice_assistant/room/{room_id}/session/{session_id}/
├── wake_detected           # Wake word triggered
├── listening/start         # Recording started
├── listening/stop          # Recording stopped
├── transcript/interim      # Real-time transcription
├── transcript/final        # Final transcription
├── response/stream/start   # AI response starting
├── response/stream/chunk   # Response token
├── response/stream/complete # Response finished
└── state                   # Current state (idle, listening, etc.)
```

## Development

### Running locally (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment
export PLATFORM=macos
export AI_GATEWAY_URL=http://localhost:8080

# Run
python app/main.py
```

### Platform abstraction layer

New audio/feedback implementations can be added to `app/platforms/`:

```python
from app.platforms import get_audio_backend, get_playback_backend, get_feedback_backend

# Get platform-appropriate backends
audio = get_audio_backend()
playback = get_playback_backend()
feedback = get_feedback_backend()
```

## Related Services

- **ai-gateway**: AI processing backend (required)
- **mosquitto**: MQTT broker (required for React Dashboard)
- **react-dashboard**: Browser-based voice interface (optional)

## License

Part of the ha-enterprise-starter project.
