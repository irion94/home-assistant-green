#!/usr/bin/env python3
"""
Wake-Word Detection Service
Main entry point for continuous wake-word monitoring
"""

import os
import sys
import time
import logging
import signal
import uuid
import queue
import threading
import json
import asyncio
import re
from typing import Optional
from pathlib import Path

import httpx
import paho.mqtt.client as mqtt

from detector import WakeWordDetector
from audio_capture import AudioCapture
from ai_gateway_client import AIGatewayClient
from feedback import AudioFeedback
from transcriber import Transcriber
from whisper_transcriber import WhisperTranscriber
from parallel_stt import ParallelSTT
from streaming_transcriber import StreamingTranscriber
from tts_service import TTSService
from state_machine import VoiceStateMachine, VoiceState, SessionContext, InteractionResult

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='{"timestamp": "%(asctime)s", "logger": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


class InterruptListener:
    """Background listener for interrupt detection during TTS playback.

    Listens for wake-word or interrupt keywords while TTS is playing,
    allowing user to stop the current response.
    """

    def __init__(self, audio_capture, detector, threshold: float = 0.3):
        """Initialize interrupt listener.

        Args:
            audio_capture: AudioCapture instance
            detector: WakeWordDetector instance
            threshold: Detection threshold (lower than normal for interrupts)
        """
        self.audio_capture = audio_capture
        self.detector = detector
        self.threshold = threshold
        self.listening = False
        self.interrupted = False
        self.worker = None
        logger.info(f"Interrupt listener initialized (threshold: {threshold})")

    def start(self):
        """Start listening for interrupts in background."""
        if self.listening:
            return
        self.listening = True
        self.interrupted = False
        self.worker = threading.Thread(target=self._listen_loop, daemon=True)
        self.worker.start()
        logger.info("Interrupt listener started")

    def stop(self):
        """Stop listening for interrupts."""
        self.listening = False
        if self.worker:
            self.worker.join(timeout=1.0)
            self.worker = None
        logger.info("Interrupt listener stopped")

    def was_interrupted(self) -> bool:
        """Check if interrupt was detected."""
        return self.interrupted

    def _listen_loop(self):
        """Background loop that listens for wake-word during TTS."""
        while self.listening:
            try:
                # Get audio chunk (non-blocking)
                audio_chunk = self.audio_capture.get_chunk()
                if audio_chunk is None:
                    time.sleep(0.05)
                    continue

                # Check for wake-word (with lower threshold)
                prediction = self.detector.predict(audio_chunk)
                if prediction >= self.threshold:
                    logger.info(f"Interrupt detected! (confidence: {prediction:.2f})")
                    self.interrupted = True
                    self.listening = False
                    break

            except Exception as e:
                logger.debug(f"Interrupt listener error: {e}")
                time.sleep(0.1)


class TTSQueue:
    """Queue for managing TTS sentence playback.

    Plays sentences sequentially without gaps, allowing streaming
    responses to start playing while still receiving more sentences.
    """

    def __init__(self, tts_service):
        """Initialize TTS queue.

        Args:
            tts_service: TTSService instance for audio playback
        """
        self.tts_service = tts_service
        self.queue = queue.Queue()
        self.playing = False
        self.should_stop = False
        self.worker = threading.Thread(target=self._worker, daemon=True)
        self.worker.start()
        logger.info("TTS queue initialized")

    def _worker(self):
        """Worker thread that processes sentences from queue."""
        while True:
            try:
                sentence = self.queue.get(timeout=1.0)
                if sentence is None:
                    break
                if self.should_stop:
                    self.queue.task_done()
                    continue
                self.playing = True
                logger.info(f"TTS playing: {sentence[:50]}...")
                self.tts_service.speak(sentence)
                self.playing = False
                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"TTS queue error: {e}")
                self.playing = False

    def add(self, sentence: str):
        """Add sentence to playback queue.

        Args:
            sentence: Text to speak
        """
        if not self.should_stop:
            self.queue.put(sentence)

    def clear(self):
        """Clear all pending sentences from queue."""
        self.should_stop = True
        while not self.queue.empty():
            try:
                self.queue.get_nowait()
                self.queue.task_done()
            except queue.Empty:
                break
        self.should_stop = False
        logger.info("TTS queue cleared")

    def wait_completion(self):
        """Wait for all queued sentences to finish playing."""
        self.queue.join()

    def stop(self):
        """Stop the worker thread."""
        self.queue.put(None)
        self.worker.join(timeout=2.0)


def setup_model_symlinks():
    """
    Copy preprocessing models to OpenWakeWord package directory
    This allows OpenWakeWord to find our custom models
    """
    import openwakeword
    import shutil

    package_models_dir = Path(openwakeword.__file__).parent / "resources" / "models"
    custom_models_dir = Path("/app/models")

    logger.info(f"Package models dir: {package_models_dir}")
    logger.info(f"Custom models dir: {custom_models_dir}")

    # Create package models directory if it doesn't exist
    try:
        package_models_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created package models directory: {package_models_dir}")
    except Exception as e:
        logger.error(f"Failed to create package models directory: {e}")

    # Get inference framework to determine which model files to copy
    inference_framework = os.getenv("INFERENCE_FRAMEWORK", "tflite")
    ext = ".onnx" if inference_framework == "onnx" else ".tflite"

    # List what's actually in the custom models directory
    try:
        if custom_models_dir.exists():
            files = list(custom_models_dir.glob(f"*{ext}"))
            logger.info(f"Found {len(files)} {ext} files in {custom_models_dir}")
            for f in files:
                logger.info(f"  - {f.name}")
        else:
            logger.warning(f"Custom models directory does not exist: {custom_models_dir}")
    except Exception as e:
        logger.error(f"Error listing custom models: {e}")

    # Models that need to be copied (preprocessing models for OpenWakeWord)
    preprocessing_models = [f"melspectrogram{ext}", f"embedding_model{ext}"]

    for model_file in preprocessing_models:
        source = custom_models_dir / model_file
        target = package_models_dir / model_file

        logger.info(f"Checking {model_file}: source exists={source.exists()}, target exists={target.exists()}")

        if source.exists():
            if target.exists():
                logger.info(f"Model already exists in package: {model_file}")
            else:
                try:
                    logger.info(f"Copying {source} -> {target}")
                    shutil.copy2(source, target)
                    logger.info(f"Copied {model_file} to package directory")
                    sys.stdout.flush()  # Ensure log appears before crash
                except Exception as e:
                    logger.error(f"Failed to copy {model_file}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
        else:
            logger.warning(f"Source model not found: {source}")


class WakeWordService:
    """Main wake-word detection service"""

    def __init__(self):
        self.running = False
        self.audio_capture: Optional[AudioCapture] = None
        self.detector: Optional[WakeWordDetector] = None
        self.ai_client: Optional[AIGatewayClient] = None
        self.feedback: Optional[AudioFeedback] = None
        self.parallel_stt: Optional[ParallelSTT] = None
        self.streaming_stt: Optional[StreamingTranscriber] = None
        self.tts_service: Optional[TTSService] = None
        self.tts_queue: Optional[TTSQueue] = None
        self.interrupt_listener: Optional[InterruptListener] = None
        self.mqtt_client: Optional[mqtt.Client] = None

        # Parallel TTS support (for Phase X: reduced latency via parallel synthesis)
        self.parallel_tts_queue = None  # Lazy init to ParallelTTSQueue
        self.sentence_buffer = ""  # Token buffer for sentence extraction
        self.sentence_endings = {'.', '!', '?'}  # Sentence boundary markers

        # MQTT command flags
        self.conversation_start_requested = False
        self.conversation_stop_requested = False

        # Conversation mode configuration
        # Default to single-command mode (false = one command then close)
        self.conversation_mode_enabled = os.getenv("CONVERSATION_MODE_DEFAULT", "false").lower() == "true"

        # Room identification for multi-device support
        self.room_id = os.getenv("ROOM_ID", "default")  # Default room for wake-word detection
        self._session_room_id = self.room_id  # Active session room (can be overridden via MQTT command)
        self._session_source = "wake_word"  # Session source: 'wake_word', 'dashboard', or 'api'

        # State machine (initialized in setup after room_id is set)
        self.state_machine: Optional[VoiceStateMachine] = None

        # Configuration from environment
        self.audio_device = os.getenv("AUDIO_DEVICE", "hw:2,0")
        self.sample_rate = int(os.getenv("SAMPLE_RATE", "16000"))
        self.channels = int(os.getenv("CHANNELS", "6"))
        self.chunk_size = int(os.getenv("CHUNK_SIZE", "1280"))
        self.wake_word_model = os.getenv("WAKE_WORD_MODEL", "hey_jarvis_v0.1")
        self.detection_threshold = float(os.getenv("DETECTION_THRESHOLD", "0.5"))
        self.recording_duration = int(os.getenv("RECORDING_DURATION", "7"))
        self.conversation_timeout = int(os.getenv("CONVERSATION_TIMEOUT", "30"))

        # Streaming STT configuration
        self.streaming_stt_enabled = os.getenv("STREAMING_STT_ENABLED", "true").lower() == "true"
        self.streaming_stt_confidence_threshold = float(os.getenv("STREAMING_STT_CONFIDENCE_THRESHOLD", "0.7"))
        self.vosk_model_path: Optional[str] = None

    def setup(self):
        """Initialize all components"""
        logger.info("Initializing Wake-Word Detection Service")
        logger.info(f"Audio device: {self.audio_device}")
        logger.info(f"Sample rate: {self.sample_rate} Hz")
        logger.info(f"Channels: {self.channels}")
        logger.info(f"Wake word model: {self.wake_word_model}")
        logger.info(f"Detection threshold: {self.detection_threshold}")

        try:
            # Initialize audio capture
            self.audio_capture = AudioCapture(
                device=self.audio_device,
                sample_rate=self.sample_rate,
                channels=self.channels,
                chunk_size=self.chunk_size
            )
            logger.info("Audio capture initialized")

            # Initialize wake-word detector
            self.detector = WakeWordDetector(
                model_name=self.wake_word_model,
                threshold=self.detection_threshold
            )
            logger.info("Wake-word detector initialized")

            # Initialize AI Gateway client
            ai_gateway_url = os.getenv("AI_GATEWAY_URL", "http://host.docker.internal:8080")
            self.ai_client = AIGatewayClient(base_url=ai_gateway_url)
            logger.info(f"AI Gateway client initialized: {ai_gateway_url}")

            # Initialize audio feedback
            enable_beep = os.getenv("ENABLE_BEEP", "true").lower() == "true"
            self.feedback = AudioFeedback(enabled=enable_beep)
            logger.info(f"Audio feedback initialized (enabled: {enable_beep})")

            # Initialize parallel STT (Vosk + optional Whisper) for local speech-to-text
            self.vosk_model_path = os.getenv("VOSK_MODEL_PATH")
            whisper_model_size = os.getenv("WHISPER_MODEL_SIZE", "base")
            self.parallel_stt = ParallelSTT(
                vosk_model_path=self.vosk_model_path,
                whisper_model_size=whisper_model_size
            )
            # Log message now comes from ParallelSTT.__init__() based on USE_WHISPER flag

            # Initialize streaming STT (Vosk only) for real-time interim results
            if self.streaming_stt_enabled and self.vosk_model_path:
                self.streaming_stt = StreamingTranscriber(
                    model_path=self.vosk_model_path,
                    sample_rate=self.sample_rate
                )
                logger.info(f"Streaming STT initialized (Vosk, confidence threshold: {self.streaming_stt_confidence_threshold})")
            else:
                logger.info(f"Streaming STT disabled (enabled={self.streaming_stt_enabled})")

            # Initialize TTS service for local text-to-speech
            self.tts_service = TTSService()
            logger.info("TTS service initialized for local speech output")

            # Preload XTTS if parallel TTS is enabled (avoid lazy loading delay)
            if os.getenv("PARALLEL_TTS_ENABLED", "false").lower() == "true":
                logger.info("Parallel TTS enabled - preloading XTTS model...")
                self.tts_service.preload_xtts()

            # Initialize TTS queue for streaming playback
            self.tts_queue = TTSQueue(self.tts_service)
            logger.info("TTS queue initialized for streaming playback")

            # Initialize interrupt listener for TTS interruption
            interrupt_threshold = float(os.getenv("INTERRUPT_THRESHOLD", "0.3"))
            self.interrupt_listener = InterruptListener(
                self.audio_capture,
                self.detector,
                threshold=interrupt_threshold
            )
            logger.info(f"Interrupt listener initialized (threshold: {interrupt_threshold})")

            # Initialize MQTT client for status updates and commands
            mqtt_host = os.getenv("MQTT_HOST", "host.docker.internal")
            mqtt_port = int(os.getenv("MQTT_PORT", "1883"))
            try:
                self.mqtt_client = mqtt.Client(client_id=f"wake-word-{self.room_id}")
                self.mqtt_client.on_message = self._on_mqtt_message
                self.mqtt_client.connect(mqtt_host, mqtt_port, 60)
                # Subscribe to ALL rooms using wildcard (+) for multi-device support
                # v1 topics (Phase 5 migration)
                self.mqtt_client.subscribe(f"v1/voice_assistant/room/+/command/#")
                self.mqtt_client.subscribe(f"v1/voice_assistant/room/+/config/conversation_mode")
                # v0 legacy topics (backward compatibility)
                self.mqtt_client.subscribe(f"voice_assistant/room/+/command/#")
                self.mqtt_client.subscribe(f"voice_assistant/room/+/config/conversation_mode")
                self.mqtt_client.subscribe("voice_assistant/command")
                self.mqtt_client.subscribe("voice_assistant/config/conversation_mode")
                self.mqtt_client.loop_start()
                logger.info(f"MQTT client connected to {mqtt_host}:{mqtt_port}")
                logger.info(f"Default room ID: {self.room_id} (wake-word detection)")
                logger.info(f"Subscribed to ALL room topics: voice_assistant/room/+/...")
                logger.info(f"Conversation mode default: {self.conversation_mode_enabled}")
            except Exception as mqtt_error:
                logger.warning(f"MQTT connection failed: {mqtt_error} - status updates disabled")
                self.mqtt_client = None

            # Initialize state machine (after MQTT for status callbacks)
            self.state_machine = VoiceStateMachine(
                room_id=self.room_id,
                on_state_change=self._on_state_change
            )
            logger.info(f"State machine initialized (room_id={self.room_id})")

            # Publish initial idle status
            self.publish_status("idle")

        except Exception as e:
            logger.error(f"Failed to initialize service: {e}")
            raise

    def _on_state_change(
        self,
        old_state: VoiceState,
        new_state: VoiceState,
        session: Optional[SessionContext]
    ) -> None:
        """Callback for state machine transitions - publishes MQTT status."""
        status = self.state_machine.get_status_string() if self.state_machine else "idle"
        session_id = session.session_id if session else None
        self.publish_session_state(status, session_id)

    def publish_status(self, status: str, text: str = ""):
        """Publish status update via MQTT (not retained to avoid stale status).

        Publishes to both legacy and room-scoped topics for compatibility.
        """
        if self.mqtt_client:
            try:
                # Legacy topic (for backward compatibility during migration)
                self.mqtt_client.publish("voice_assistant/status", status, retain=False)
                if text:
                    self.mqtt_client.publish("voice_assistant/text", text, retain=False)

                # Room-scoped topic (new format)
                session_id = self.state_machine.session.session_id if (
                    self.state_machine and self.state_machine.session
                ) else None
                self.publish_session_state(status, session_id, text)
            except Exception as e:
                logger.warning(f"Failed to publish MQTT status: {e}")

    def publish_session_state(self, status: str, session_id: Optional[str] = None, text: str = ""):
        """Publish session state to room-scoped MQTT topics (v0 + v1).

        Publishes to BOTH v0 (legacy) and v1 (Phase 5 migration) topics:
        - v0: voice_assistant/room/{room_id}/session/active
        - v1: v1/voice_assistant/room/{room_id}/session/active
        - v0: voice_assistant/room/{room_id}/session/{session_id}/state
        - v1: v1/voice_assistant/room/{room_id}/session/{session_id}/state
        """
        if not self.mqtt_client:
            return

        try:
            # Publish to BOTH v0 (legacy) and v1 (new) topics for migration period
            base_topics = [
                f"voice_assistant/room/{self._session_room_id}",  # v0
                f"v1/voice_assistant/room/{self._session_room_id}",  # v1
            ]

            for base_topic in base_topics:
                # Publish active session ID
                active_session = session_id if session_id else "none"
                self.mqtt_client.publish(f"{base_topic}/session/active", active_session, retain=True)

                # Publish session state if we have a session
                if session_id:
                    state_data = json.dumps({
                        "status": status,
                        "text": text,
                        "timestamp": time.time()
                    })
                    self.mqtt_client.publish(
                        f"{base_topic}/session/{session_id}/state",
                        state_data,
                        retain=False
                    )
        except Exception as e:
            logger.warning(f"Failed to publish session state: {e}")

    def publish_message(self, msg_type: str, text: str, session_id: str = ""):
        """Publish conversation message for kiosk display.

        Publishes to both legacy and room-scoped topics.

        Args:
            msg_type: 'transcript' or 'response'
            text: Message text
            session_id: Session identifier
        """
        if self.mqtt_client:
            try:
                message_data = json.dumps({
                    "type": msg_type,
                    "text": text,
                    "session_id": session_id,
                    "room_id": self._session_room_id,  # Use session room, not default room
                    "timestamp": time.time()
                })

                # Legacy topic (backward compatibility)
                self.mqtt_client.publish(f"voice_assistant/{msg_type}", message_data)

                # Room-scoped topic (new format)
                if session_id:
                    self.mqtt_client.publish(
                        f"voice_assistant/room/{self._session_room_id}/session/{session_id}/{msg_type}",
                        message_data
                    )

                logger.info(f"Published MQTT {msg_type}: '{text[:50]}...' to session {session_id}")
            except Exception as e:
                logger.warning(f"Failed to publish MQTT message: {e}")

    def publish_interim_transcript(self, session_id: str, text: str, sequence: int):
        """Publish interim (partial) transcript for streaming STT.

        Args:
            session_id: Session identifier
            text: Partial transcription text
            sequence: Sequence number (increments with each partial)
        """
        if not self.mqtt_client or not session_id:
            return

        try:
            topic = f"voice_assistant/room/{self._session_room_id}/session/{session_id}/transcript/interim"
            payload = json.dumps({
                "text": text,
                "is_final": False,
                "sequence": sequence,
                "timestamp": time.time()
            })
            self.mqtt_client.publish(topic, payload)
            logger.debug(f"Published interim transcript [{sequence}]: '{text[:30]}...'")
        except Exception as e:
            logger.warning(f"Failed to publish interim transcript: {e}")

    def publish_final_transcript(self, session_id: str, text: str, confidence: float, engine: str = "vosk"):
        """Publish final transcript from streaming STT.

        Args:
            session_id: Session identifier
            text: Final transcription text
            confidence: Confidence score (0.0-1.0)
            engine: STT engine used (default: vosk)
        """
        if not self.mqtt_client or not session_id:
            return

        try:
            topic = f"voice_assistant/room/{self._session_room_id}/session/{session_id}/transcript/final"
            payload = json.dumps({
                "text": text,
                "is_final": True,
                "engine": engine,
                "confidence": confidence,
                "timestamp": time.time()
            })
            self.mqtt_client.publish(topic, payload)
            logger.info(f"Published final transcript: '{text[:50]}...' (confidence={confidence:.2f})")

            # Note: Legacy transcript topic not needed - frontend uses transcript/final
            # self.publish_message("transcript", text, session_id)
        except Exception as e:
            logger.warning(f"Failed to publish final transcript: {e}")

    def publish_refined_transcript(self, session_id: str, text: str):
        """Publish Whisper-refined transcript (when Vosk confidence was low).

        Args:
            session_id: Session identifier
            text: Refined transcription text from Whisper
        """
        if not self.mqtt_client or not session_id:
            return

        try:
            topic = f"voice_assistant/room/{self._session_room_id}/session/{session_id}/transcript/refined"
            payload = json.dumps({
                "text": text,
                "is_final": True,
                "engine": "whisper",
                "is_refinement": True,
                "timestamp": time.time()
            })
            self.mqtt_client.publish(topic, payload)
            logger.info(f"Published refined transcript: '{text[:50]}...'")
        except Exception as e:
            logger.warning(f"Failed to publish refined transcript: {e}")

    def _publish_streaming_start(self, session_id: str):
        """Publish streaming response start event.

        Args:
            session_id: Session identifier
        """
        if not self.mqtt_client or not session_id:
            return

        try:
            topic = f"voice_assistant/room/{self._session_room_id}/session/{session_id}/response/stream/start"
            payload = json.dumps({"started_at": time.time()})
            self.mqtt_client.publish(topic, payload)
            logger.debug("Published streaming start")
        except Exception as e:
            logger.warning(f"Failed to publish streaming start: {e}")

    def _publish_streaming_token(self, session_id: str, token: str, sequence: int):
        """Publish single streaming response token.

        Args:
            session_id: Session identifier
            token: Token content
            sequence: Token sequence number
        """
        if not self.mqtt_client or not session_id:
            return

        try:
            topic = f"voice_assistant/room/{self._session_room_id}/session/{session_id}/response/stream/chunk"
            payload = json.dumps({
                "sequence": sequence,
                "content": token,
                "timestamp": time.time()
            })
            self.mqtt_client.publish(topic, payload)
            logger.debug(f"Published streaming token [{sequence}]: '{token[:20]}...'")
        except Exception as e:
            logger.warning(f"Failed to publish streaming token: {e}")

    def _publish_streaming_complete(self, session_id: str, full_text: str, duration: float, token_count: int):
        """Publish streaming response complete event.

        Args:
            session_id: Session identifier
            full_text: Complete response text
            duration: Processing duration in seconds
            token_count: Total number of tokens streamed
        """
        if not self.mqtt_client or not session_id:
            return

        try:
            topic = f"voice_assistant/room/{self._session_room_id}/session/{session_id}/response/stream/complete"
            payload = json.dumps({
                "text": full_text,
                "duration": duration,
                "total_tokens": token_count,
                "timestamp": time.time()
            })
            self.mqtt_client.publish(topic, payload)
            logger.info(f"Published streaming complete: {token_count} tokens in {duration:.2f}s")
        except Exception as e:
            logger.warning(f"Failed to publish streaming complete: {e}")

    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT commands.

        Handles both legacy and room-scoped topics:
        - Legacy: voice_assistant/command, voice_assistant/config/conversation_mode
        - v0: voice_assistant/room/{room_id}/command/*, voice_assistant/room/{room_id}/config/*
        - v1: v1/voice_assistant/room/{room_id}/command/*, v1/voice_assistant/room/{room_id}/config/*

        Now supports multi-room using wildcard subscriptions - extracts room_id from topic.
        """
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            logger.info(f"MQTT message received: {topic} = {payload}")

            # Remove v1 prefix if present (Phase 5 migration support)
            normalized_topic = topic.replace("v1/", "", 1) if topic.startswith("v1/") else topic

            # Room-scoped command topics (multi-room support via wildcard)
            # Topic format: voice_assistant/room/{room_id}/command/{command}
            if normalized_topic.startswith("voice_assistant/room/") and "/command/" in normalized_topic:
                parts = normalized_topic.split("/")
                if len(parts) >= 5:  # voice_assistant/room/{room_id}/command/{command}
                    room_id = parts[2]  # Extract room_id from topic
                    command = parts[-1]  # Get last part: start, stop

                    # FILTER: Only process commands for THIS device's room
                    if room_id != self.room_id:
                        logger.debug(f"Ignoring command '{command}' for room '{room_id}' (this device is '{self.room_id}')")
                        return

                    logger.info(f"Received command '{command}' for room '{room_id}'")
                    # Temporarily override room_id for this session
                    self._handle_command(command, payload, room_id)

            # Room-scoped config topics
            elif normalized_topic.startswith("voice_assistant/room/") and "/config/conversation_mode" in normalized_topic:
                parts = normalized_topic.split("/")
                if len(parts) >= 5:
                    room_id = parts[2]

                    # FILTER: Only process config for THIS device's room
                    if room_id != self.room_id:
                        logger.debug(f"Ignoring conversation mode change for room '{room_id}' (this device is '{self.room_id}')")
                        return

                    logger.info(f"Conversation mode change for room '{room_id}'")
                    self._handle_conversation_mode_change(payload)

            # Legacy topics (backward compatibility)
            elif normalized_topic == "voice_assistant/command":
                if payload == "start_conversation":
                    self._handle_command("start", "", self.room_id)
                elif payload == "stop_conversation":
                    self._handle_command("stop", "", self.room_id)
            elif normalized_topic == "voice_assistant/config/conversation_mode":
                self._handle_conversation_mode_change(payload)

        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def _handle_command(self, command: str, payload: str, room_id: str | None = None) -> None:
        """Handle voice assistant commands.

        Args:
            command: 'start' or 'stop'
            payload: Optional JSON payload with mode, source info
            room_id: Room identifier (overrides default room_id for this session)
        """
        if command == "start":
            # Temporarily override room_id for multi-room support
            if room_id:
                self._session_room_id = room_id
                logger.info(f"MQTT command: start session for room '{room_id}'")
            else:
                self._session_room_id = self.room_id
                logger.info("MQTT command: start session")

            self.conversation_start_requested = True
            self.conversation_stop_requested = False
            # Parse payload for mode and source if provided
            if payload:
                try:
                    data = json.loads(payload)

                    # Extract source (dashboard, wake_word, api)
                    if "source" in data:
                        self._session_source = data["source"]
                        logger.info(f"Session source: {self._session_source}")
                    else:
                        self._session_source = "wake_word"  # Default for backward compatibility

                    # Extract mode (single vs multi-turn conversation)
                    if "mode" in data:
                        self.conversation_mode_enabled = data["mode"] == "multi"
                        logger.info(f"Session mode set to: {'multi-turn' if self.conversation_mode_enabled else 'single'}")
                        # Publish mode change back to dashboard for UI update
                        if self.mqtt_client:
                            self.mqtt_client.publish(
                                f"voice_assistant/room/{self._session_room_id}/config/conversation_mode",
                                "true" if self.conversation_mode_enabled else "false",
                                retain=True
                            )
                            logger.info(f"Published conversation mode: {self.conversation_mode_enabled}")
                except json.JSONDecodeError:
                    pass
            else:
                # No payload = wake-word trigger
                self._session_source = "wake_word"
        elif command == "stop":
            logger.info("MQTT command: stop session")
            self.conversation_stop_requested = True

    def _handle_conversation_mode_change(self, payload: str) -> None:
        """Handle conversation mode toggle.

        Args:
            payload: 'true'/'false' or '1'/'0' or 'on'/'off'
        """
        enabled = payload.lower() in ["true", "1", "on"]
        old_mode = self.conversation_mode_enabled
        self.conversation_mode_enabled = enabled
        if old_mode != enabled:
            logger.info(f"Conversation mode {'enabled' if enabled else 'disabled'} via MQTT")
            # Publish back to confirm (for bidirectional sync)
            if self.mqtt_client:
                self.mqtt_client.publish(
                    f"voice_assistant/room/{self._session_room_id}/config/conversation_mode",
                    "true" if enabled else "false",
                    retain=True
                )

    def request_browser_stt(self, session_id: str) -> Optional[str]:
        """Request browser STT via MQTT, wait for response or timeout.

        Args:
            session_id: Session identifier

        Returns:
            str: Transcribed text from browser (if successful)
            None: If timeout or browser unavailable
        """
        if not self.mqtt_client:
            logger.warning("[Hybrid STT] MQTT client not available")
            return None

        response_topic = f"voice_assistant/room/{self._session_room_id}/session/{session_id}/stt/response"
        response_received = threading.Event()
        transcription = {"text": None, "source": None}

        def on_response(client, userdata, msg):
            try:
                payload = json.loads(msg.payload.decode())
                transcription["text"] = payload.get("text")
                transcription["source"] = payload.get("source")
                response_received.set()
            except Exception as e:
                logger.error(f"[Hybrid STT] Error parsing response: {e}")

        # Subscribe to response topic
        self.mqtt_client.subscribe(response_topic)
        self.mqtt_client.message_callback_add(response_topic, on_response)

        # Publish request
        request_topic = f"voice_assistant/room/{self._session_room_id}/session/{session_id}/stt/request"
        request_payload = json.dumps({
            "type": "start",
            "sessionId": session_id,
            "timestamp": int(time.time() * 1000),
            "timeout_ms": 5000
        })
        self.mqtt_client.publish(request_topic, request_payload)

        logger.info(f"[Hybrid STT] Requested browser STT (session: {session_id})")

        # Wait for response with timeout
        timeout_seconds = float(os.getenv("HYBRID_STT_TIMEOUT_MS", "5000")) / 1000.0
        if response_received.wait(timeout=timeout_seconds):
            logger.info(f"[Hybrid STT] Browser responded: source={transcription['source']}, text='{transcription['text'][:50] if transcription['text'] else 'None'}...'")
            self.mqtt_client.unsubscribe(response_topic)
            return transcription["text"]
        else:
            logger.warning(f"[Hybrid STT] Browser timeout after {timeout_seconds}s, falling back to RPI STT")
            # Publish timeout notification
            timeout_topic = f"voice_assistant/room/{self._session_room_id}/session/{session_id}/stt/timeout"
            timeout_payload = json.dumps({
                "reason": "no_response",
                "timestamp": int(time.time() * 1000)
            })
            self.mqtt_client.publish(timeout_topic, timeout_payload)
            self.mqtt_client.unsubscribe(response_topic)
            return None

    def process_interaction(self, session_id: str) -> InteractionResult:
        """Process a single voice interaction.

        Unified method that handles one complete interaction cycle:
        1. Record audio (LISTENING state) - with streaming STT if enabled
        2. Transcribe speech (TRANSCRIBING state) - Whisper refinement if needed
        3. Get LLM response (PROCESSING state)
        4. Play TTS response (SPEAKING state)

        Args:
            session_id: Session identifier

        Returns:
            InteractionResult with transcript, response, and flags
        """
        result = InteractionResult()

        try:
            # LISTENING - Record user speech (with optional streaming STT or hybrid browser STT)
            self.state_machine.transition(VoiceState.LISTENING)
            self.feedback.play_listening()
            logger.info("Listening for speech...")

            stt_start = time.time()

            # Check if hybrid STT (browser first) is enabled
            hybrid_enabled = os.getenv("HYBRID_STT_ENABLED", "false").lower() == "true"
            browser_text = None
            audio_data = None
            vosk_text = None
            vosk_confidence = 0.0

            if hybrid_enabled:
                # HYBRID MODE: Try browser STT first
                # Give browser time to subscribe to MQTT topics after session creation
                logger.info("[Hybrid STT] Waiting for browser to subscribe...")
                time.sleep(0.3)  # 300ms delay for browser MQTT subscription
                logger.info("[Hybrid STT] Attempting browser STT first...")
                browser_text = self.request_browser_stt(session_id)

                if browser_text:
                    # Browser STT succeeded - skip audio recording
                    logger.info(f"[Hybrid STT] Using browser transcription: '{browser_text[:50]}...'")
                    result.transcript = browser_text
                    result.stt_engine = "browser"
                    result.stt_duration = time.time() - stt_start

                    # Publish transcript to MQTT for frontend display
                    self.publish_message("transcript", browser_text, session_id)
                    logger.info(f"[Hybrid STT] Published browser transcript to MQTT")
                else:
                    # Browser timeout - fall back to local STT
                    logger.info("[Hybrid STT] Falling back to local RPI STT...")
                    # Continue to audio recording below

            # Local STT (if hybrid disabled or browser timed out)
            if not hybrid_enabled or not browser_text:
                # Use streaming STT if enabled
                if self.streaming_stt_enabled and self.streaming_stt:
                    audio_data, vosk_text, vosk_confidence = self._process_streaming_stt(session_id)
                else:
                    # Fallback to batch mode
                    audio_data = self.audio_capture.record(
                        duration=self.recording_duration,
                        stop_check=lambda: self.conversation_stop_requested
                    )
                    vosk_text = None
                    vosk_confidence = 0.0

                # Check for stop during recording
                if self.conversation_stop_requested:
                    result.should_continue = False
                    return result

                logger.info(f"Recorded {len(audio_data)} audio frames")

                # TRANSCRIBING - Convert speech to text (or refine streaming result)
                self.state_machine.transition(VoiceState.TRANSCRIBING)
                self.feedback.processing()

                if self.streaming_stt_enabled and vosk_text:
                    # Streaming mode: use Vosk result, optionally refine with Whisper
                    result.transcript = vosk_text
                    result.stt_engine = "vosk"

                    # Check if Whisper refinement needed (low confidence)
                    if vosk_confidence < self.streaming_stt_confidence_threshold:
                        logger.info(f"Low confidence ({vosk_confidence:.2f}), running Whisper refinement...")
                        whisper_result = self.parallel_stt.whisper.transcribe(audio_data, self.sample_rate)
                        if whisper_result and whisper_result.strip():
                            result.transcript = whisper_result
                            result.stt_engine = "whisper"
                            self.publish_refined_transcript(session_id, whisper_result)
                            logger.info(f"Whisper refined: '{whisper_result[:50]}...'")
                else:
                    # Batch mode: use parallel STT
                    stt_result = self.parallel_stt.transcribe_parallel(audio_data, self.sample_rate)
                    result.transcript = stt_result.selected.text
                    result.stt_engine = stt_result.selected.engine
                    # Publish STT comparison for debugging
                    self._publish_stt_comparison(stt_result, session_id)

                result.stt_duration = time.time() - stt_start

            if not result.transcript:
                logger.info("No speech detected")
                result.should_continue = True  # Continue listening in multi-turn
                return result

            logger.info(f"Transcribed: '{result.transcript}' (via {result.stt_engine})")

            # Only publish via legacy method if not using streaming (streaming publishes via final topic)
            if not self.streaming_stt_enabled:
                self.publish_message("transcript", result.transcript, session_id)

            # Check for end command keywords
            result.is_end_command = self._is_end_command(result.transcript)
            if result.is_end_command:
                logger.info(f"End command detected: '{result.transcript}'")
                result.should_continue = False
                return result

            # PROCESSING - Get LLM response (streaming)
            self.state_machine.transition(VoiceState.PROCESSING)
            self.feedback.processing()

            # Publish streaming start
            self._publish_streaming_start(session_id)

            # Track streaming state
            llm_start = time.time()
            token_count = 0

            # Define callback for streaming tokens
            def on_token(token: str, sequence: int):
                nonlocal token_count
                token_count = sequence
                self._publish_streaming_token(session_id, token, sequence)

                # Skip TTS buffering for dashboard sessions (browser handles TTS)
                if self._session_source == "dashboard":
                    return

                # Parallel TTS: buffer tokens and enqueue complete sentences (for wake-word sessions only)
                if self._parallel_tts_enabled():
                    self.sentence_buffer += token
                    # Log first few tokens to verify callback is working
                    if sequence <= 3:
                        logger.info(f"Token #{sequence}: '{token}' (buffer: {len(self.sentence_buffer)} chars)")

                    # Check for sentence endings (.!?)
                    for i, char in enumerate(self.sentence_buffer):
                        if char in self.sentence_endings:
                            # Verify it's really an ending (not abbreviation like "Dr.")
                            if i + 1 >= len(self.sentence_buffer) or self.sentence_buffer[i + 1] in ' \n':
                                # Extract complete sentence
                                sentence = self.sentence_buffer[:i + 1].strip()
                                self.sentence_buffer = self.sentence_buffer[i + 1:].lstrip()

                                if sentence:
                                    # Enqueue for background synthesis (detect language from first sentence)
                                    lang = self._detect_language(sentence)
                                    logger.info(f"Enqueueing TTS ({lang}): '{sentence[:40]}...'")
                                    self._get_parallel_tts_queue().enqueue(sentence, lang)
                                break

            # Stream response from AI Gateway
            try:
                full_response = asyncio.run(
                    self.ai_client.send_conversation_stream(
                        text=result.transcript,
                        session_id=session_id,
                        on_token=on_token
                    )
                )
            except Exception as e:
                logger.error(f"Error during streaming: {e}")
                full_response = None

            result.llm_duration = time.time() - llm_start

            # Publish streaming complete
            if full_response:
                self._publish_streaming_complete(session_id, full_response, result.llm_duration, token_count)
                result.response = full_response
            else:
                logger.warning("No response from AI Gateway streaming")
                result.error = "No response from AI Gateway"
                self.feedback.play_error()
                return result

            # Note: Streaming endpoint doesn't return conversation mode action metadata
            # Conversation mode is now controlled via MQTT commands from the dashboard

            # SPEAKING - Play TTS response
            if result.response:
                # Skip local TTS for dashboard sessions (browser will handle TTS via Web Speech API)
                if self._session_source == "dashboard":
                    logger.info(f"Skipping local TTS playback for dashboard session (room={self._session_room_id})")
                    self.state_machine.transition(VoiceState.SPEAKING)
                    self.feedback.speaking()
                    # Browser will handle TTS via streaming response
                    self.feedback.play_success()
                else:
                    # Local TTS for wake-word sessions (RPi microphone/speaker)
                    self.state_machine.transition(VoiceState.SPEAKING)
                    self.feedback.speaking()
                    # Note: Legacy response topic not needed - streaming already published complete text
                    # via stream/complete topic, which frontend uses to finalize the message
                    # self.publish_message("response", result.response, session_id)

                    tts_start = time.time()

                    if self._parallel_tts_enabled():
                        # === PARALLEL TTS MODE ===
                        logger.info("Starting parallel TTS playback...")

                        # Enqueue any remaining buffer (last sentence fragment)
                        if self.sentence_buffer.strip():
                            lang = self._detect_language(result.transcript)
                            self._get_parallel_tts_queue().enqueue(self.sentence_buffer.strip(), lang)
                            self.sentence_buffer = ""

                        # Play all queued audio chunks (blocks until queue empty)
                        chunk_count = 0
                        queue_timeout = float(os.getenv("PARALLEL_TTS_QUEUE_TIMEOUT", "30"))
                        while self._get_parallel_tts_queue().has_pending():
                            if not self._get_parallel_tts_queue().play_next(timeout=queue_timeout):
                                break  # Interrupted, timeout, or error
                            chunk_count += 1

                        result.tts_duration = time.time() - tts_start
                        logger.info(f"Parallel TTS complete: {chunk_count} chunks in {result.tts_duration:.1f}s")

                    else:
                        # === LEGACY MODE (fallback) ===
                        logger.info(f"Speaking (legacy): '{result.response[:50]}...'")
                        self.tts_service.speak(result.response)
                        result.tts_duration = time.time() - tts_start
                        logger.info("TTS playback complete")

                    self.feedback.play_success()

            # Update session activity
            if self.state_machine.session:
                self.state_machine.session.increment_turn()

        except Exception as e:
            logger.error(f"Error in process_interaction: {e}")
            result.error = str(e)
            self.feedback.play_error()

        return result

    def _is_end_command(self, text: str) -> bool:
        """Check if text contains conversation end keywords.

        Uses word boundary matching to avoid false positives (e.g., "pa" in "sypialni").

        Args:
            text: User transcript

        Returns:
            True if end command detected
        """
        text_lower = text.lower()
        end_keywords = [
            "stop", "koniec", "wystarczy", "to wszystko", "bye", "goodbye",
            "end conversation", "zakończ", "dziękuję", "dzięki", "pa",
            "do widzenia", "skończ", "koniec rozmowy", "end"
        ]
        # Use word boundary regex to avoid substring false positives
        for keyword in end_keywords:
            pattern = r'\b' + re.escape(keyword) + r'\b'
            if re.search(pattern, text_lower):
                return True
        return False

    def _publish_stt_comparison(self, stt_result, session_id: str) -> None:
        """Publish STT comparison results for debugging.

        Args:
            stt_result: ParallelSTTResult
            session_id: Session identifier
        """
        if not self.mqtt_client:
            return

        try:
            comparison_data = json.dumps({
                "vosk": {
                    "text": stt_result.vosk.text,
                    "duration": round(stt_result.vosk.duration, 2)
                },
                "whisper": {
                    "text": stt_result.whisper.text,
                    "duration": round(stt_result.whisper.duration, 2)
                },
                "selected": stt_result.selected.engine,
                "reason": stt_result.selection_reason,
                "session_id": session_id
            })
            self.mqtt_client.publish("voice_assistant/stt_comparison", comparison_data)
        except Exception as e:
            logger.warning(f"Failed to publish STT comparison: {e}")

    def _parallel_tts_enabled(self) -> bool:
        """Check if parallel TTS feature is enabled.

        When enabled, forces XTTS mode for all responses to ensure
        consistent synthesis latency suitable for parallel processing.

        Returns:
            True if PARALLEL_TTS_ENABLED env var is true
        """
        enabled = os.getenv("PARALLEL_TTS_ENABLED", "false").lower() == "true"

        if enabled:
            # Force XTTS for all responses (parallel TTS requires consistent latency)
            self.tts_service.enable_xtts = True
            self.tts_service.short_threshold = 0  # No VITS routing

        return enabled

    def _get_parallel_tts_queue(self):
        """Get or create ParallelTTSQueue instance (lazy init).

        Returns:
            ParallelTTSQueue instance
        """
        if self.parallel_tts_queue is None:
            from tts_queue import ParallelTTSQueue
            max_workers = int(os.getenv("PARALLEL_TTS_WORKERS", "2"))
            self.parallel_tts_queue = ParallelTTSQueue(self.tts_service, max_workers=max_workers)
            logger.info(f"Initialized ParallelTTSQueue (workers={max_workers})")
        return self.parallel_tts_queue

    def _detect_language(self, text: str) -> str:
        """Detect language from text (delegate to TTS service).

        Args:
            text: Text to analyze

        Returns:
            Language code ('pl' or 'en')
        """
        return self.tts_service.detect_language(text)

    def _process_streaming_stt(self, session_id: str) -> tuple:
        """Process audio with streaming STT for real-time interim results.

        Records audio while simultaneously streaming it to Vosk for real-time
        partial transcriptions. Publishes interim results via MQTT for immediate
        UI feedback (Debug Panel).

        Args:
            session_id: Session identifier for MQTT topics

        Returns:
            Tuple of (audio_data, final_text, confidence):
            - audio_data: Complete recorded audio as numpy array
            - final_text: Final Vosk transcription
            - confidence: Vosk confidence score (0.0-1.0)
        """
        import numpy as np

        # Reset streaming transcriber for new session
        self.streaming_stt.reset()
        logger.info("Starting streaming STT...")

        # Track sequence for interim results
        sequence_tracker = {"seq": 0}

        def on_chunk(audio_chunk: np.ndarray) -> None:
            """Process audio chunk through streaming STT and publish interim results."""
            try:
                partial_text, is_complete = self.streaming_stt.process_chunk(audio_chunk)

                if partial_text and not is_complete:
                    # New partial result - publish to MQTT for Debug Panel
                    sequence_tracker["seq"] += 1
                    self.publish_interim_transcript(
                        session_id,
                        partial_text,
                        sequence_tracker["seq"]
                    )
            except Exception as e:
                logger.error(f"Streaming STT chunk error: {e}")

        # Record audio with streaming callback
        audio_data = self.audio_capture.record_streaming(
            duration=self.recording_duration,
            on_chunk=on_chunk,
            stop_check=lambda: self.conversation_stop_requested
        )

        # Finalize transcription and get confidence
        final_text, confidence = self.streaming_stt.finalize()

        # Publish final transcript via MQTT
        if final_text:
            self.publish_final_transcript(session_id, final_text, confidence, engine="vosk")
            logger.info(f"Streaming STT complete: '{final_text[:50]}...' (confidence={confidence:.2f})")
        else:
            logger.info("Streaming STT: No speech detected")

        return audio_data, final_text, confidence

    def run_session(self, session_id: str, conversation_mode: bool) -> None:
        """Run a voice assistant session.

        Unified method that handles both single-command and multi-turn sessions.
        Supports smart clarification: if AI asks a question in single-command mode,
        allows one follow-up turn for the user to clarify.

        NOTE: The session respects LIVE toggle changes - if user toggles conversation
        mode during the session, it affects the next turn immediately.

        Args:
            session_id: Unique session identifier
            conversation_mode: Initial mode (True for multi-turn, False for single)
        """
        mode_str = "multi-turn" if conversation_mode else "single-command"
        logger.info(f"Starting {mode_str} session (id={session_id})")

        # Start session in state machine
        self.state_machine.start_session(session_id, conversation_mode)
        self.state_machine.transition(VoiceState.WAKE_DETECTED)
        self.feedback.play_wake_detected()

        # Track if we've already done a clarification turn (prevent infinite loop)
        clarification_used = False

        try:
            timeout = self.conversation_timeout
            last_activity = time.time()

            while self.running:
                # Use LIVE conversation_mode_enabled flag (allows mid-session toggle)
                is_conversation_mode = self.conversation_mode_enabled

                # Check timeout for multi-turn
                if is_conversation_mode and (time.time() - last_activity > timeout):
                    logger.info("Session timeout reached")
                    break

                # Check for external stop signal
                if self.conversation_stop_requested:
                    logger.info("Stop signal received")
                    self.conversation_stop_requested = False
                    break

                # Process one interaction
                result = self.process_interaction(session_id)

                if result.error:
                    logger.warning(f"Interaction error: {result.error}")
                    if not is_conversation_mode:
                        break

                if result.is_end_command:
                    logger.info("End command detected, ending session")
                    self.feedback.play_success()
                    break

                if not result.should_continue:
                    break

                # Re-read conversation mode (may have changed during process_interaction)
                is_conversation_mode = self.conversation_mode_enabled

                # Single command mode - exit after one successful interaction
                # UNLESS: AI asked a clarifying question (response ends with ?)
                if not is_conversation_mode and result.transcript:
                    # Smart clarification: if response is a question, allow one follow-up
                    response_is_question = result.response and result.response.strip().endswith('?')
                    if response_is_question and not clarification_used:
                        logger.info("Response is a question - allowing clarification turn")
                        clarification_used = True
                        # Transition to WAITING state for clarity
                        self.state_machine.transition(VoiceState.WAITING)
                        last_activity = time.time()
                        continue  # Allow one more turn
                    else:
                        break  # Normal single-command exit

                # Multi-turn: transition to WAITING and update activity
                if is_conversation_mode:
                    self.state_machine.transition(VoiceState.WAITING)
                    last_activity = time.time()

        except Exception as e:
            logger.error(f"Error in session: {e}")
        finally:
            # Clean up session
            self.conversation_start_requested = False
            self.conversation_stop_requested = False
            self.state_machine.end_session()
            self.state_machine.transition(VoiceState.IDLE, force=True)
            self.publish_status("idle", "Session ended")
            self.feedback.idle()

            # Publish session ended for bidirectional sync
            if self.mqtt_client:
                self.mqtt_client.publish(
                    f"voice_assistant/room/{self._session_room_id}/session/{session_id}/ended",
                    json.dumps({"timestamp": time.time()})
                )
                # Legacy topic
                self.mqtt_client.publish("voice_assistant/conversation_ended", "true")

            logger.info(f"Session ended: {session_id}")

    def process_single_command(self, session_id: str):
        """Process a single command without entering conversation loop.

        DEPRECATED: Use run_session(session_id, conversation_mode=False) instead.

        Args:
            session_id: Unique session identifier
        """
        logger.info(f"Processing single command (session={session_id})")

        try:
            # Show listening LED
            self.feedback.play_listening()
            self.publish_status("listening")

            # Record user speech
            logger.info("Listening for single command...")
            audio_data = self.audio_capture.record(duration=self.recording_duration)
            logger.info(f"Recorded {len(audio_data)} audio frames")

            # Show processing LED
            self.feedback.processing()
            self.publish_status("processing")

            # Transcribe locally using parallel STT
            stt_result = self.parallel_stt.transcribe_parallel(audio_data, self.sample_rate)
            text = stt_result.selected.text

            if not text:
                logger.info("No speech detected")
                self.publish_status("idle", "No speech detected")
                self.feedback.idle()
                return

            logger.info(f"Transcribed: '{text}' (via {stt_result.selected.engine})")
            self.publish_status("transcribed", text)
            self.publish_message("transcript", text, session_id)

            # Publish comparison results for kiosk display
            if self.mqtt_client:
                comparison_data = json.dumps({
                    "vosk": {
                        "text": stt_result.vosk.text,
                        "duration": round(stt_result.vosk.duration, 2)
                    },
                    "whisper": {
                        "text": stt_result.whisper.text,
                        "duration": round(stt_result.whisper.duration, 2)
                    },
                    "selected": stt_result.selected.engine,
                    "reason": stt_result.selection_reason
                })
                self.mqtt_client.publish("voice_assistant/stt_comparison", comparison_data)

            # Send text to conversation endpoint
            response = self.ai_client.send_conversation_text(
                text=text,
                session_id=session_id
            )

            if not response:
                logger.warning("No response from conversation endpoint")
                self.feedback.play_error()
                self.publish_status("idle", "Error")
                return

            status = response.get("status")
            message = response.get("message", "")

            if status == "error":
                logger.warning(f"Conversation error: {message}")
                self.feedback.play_error()
                self.publish_status("idle", "Error")
                return

            # Success - play response locally via TTS
            logger.info(f"Playing response via local TTS")
            self.feedback.speaking()

            # Get response text and play locally
            response_text = response.get("text", "")
            if response_text:
                self.publish_status("speaking", response_text)
                self.publish_message("response", response_text, session_id)
                logger.info(f"Speaking: '{response_text[:50]}...'")
                self.tts_service.speak(response_text)
                logger.info("TTS playback complete")
                self.feedback.play_success()

        except Exception as e:
            logger.error(f"Error in single command processing: {e}")
            self.feedback.play_error()
        finally:
            # End conversation session
            self.ai_client.end_conversation(session_id)
            logger.info(f"Single command completed (session={session_id})")
            self.publish_status("idle", "Command completed")
            self.feedback.idle()

    def run_conversation_loop(self, session_id: str):
        """Run continuous conversation loop until exit or timeout.

        Args:
            session_id: Unique session identifier
        """
        logger.info(f"Starting conversation mode (session={session_id}, timeout={self.conversation_timeout}s)")
        self.publish_status("conversation", "Starting...")
        last_activity = time.time()

        try:
            while self.running:
                # Check for external stop signal (MQTT)
                if self.conversation_stop_requested:
                    logger.info("MQTT stop signal received")
                    self.conversation_stop_requested = False
                    self.publish_status("idle", "Stopped")
                    break

                # Check timeout
                if time.time() - last_activity > self.conversation_timeout:
                    logger.info("Conversation timeout reached")
                    self.publish_status("idle", "Timeout")
                    break

                # Show listening LED
                self.feedback.play_listening()
                self.publish_status("listening")

                # Record user speech with stop check
                logger.info("Listening for conversation input...")
                audio_data = self.audio_capture.record(
                    duration=self.recording_duration,
                    stop_check=lambda: self.conversation_stop_requested
                )

                # Check if stopped during recording
                if self.conversation_stop_requested:
                    logger.info("Stop requested during recording")
                    self.conversation_stop_requested = False
                    self.publish_status("idle", "Stopped")
                    break

                logger.info(f"Recorded {len(audio_data)} audio frames")

                # Show processing LED
                self.feedback.processing()
                self.publish_status("processing")

                # Transcribe locally using parallel STT
                stt_result = self.parallel_stt.transcribe_parallel(audio_data, self.sample_rate)
                text = stt_result.selected.text

                if not text:
                    logger.info("No speech detected, continuing conversation...")
                    continue

                logger.info(f"Transcribed: '{text}' (via {stt_result.selected.engine})")
                self.publish_status("transcribed", text)
                self.publish_message("transcript", text, session_id)

                # Publish comparison results for kiosk display
                if self.mqtt_client:
                    comparison_data = json.dumps({
                        "vosk": {
                            "text": stt_result.vosk.text,
                            "duration": round(stt_result.vosk.duration, 2)
                        },
                        "whisper": {
                            "text": stt_result.whisper.text,
                            "duration": round(stt_result.whisper.duration, 2)
                        },
                        "selected": stt_result.selected.engine,
                        "reason": stt_result.selection_reason
                    })
                    self.mqtt_client.publish("voice_assistant/stt_comparison", comparison_data)

                # Check for conversation end keywords in user's speech BEFORE sending
                text_lower = text.lower()
                end_keywords = ["stop", "koniec", "wystarczy", "to wszystko", "bye", "goodbye", "end conversation", "zakończ", "wstęp", "dziękuję", "dzięki", "pa", "do widzenia", "skończ", "koniec rozmowy"]
                should_end = any(keyword in text_lower for keyword in end_keywords)

                if should_end:
                    logger.info(f"Conversation end keyword detected in user speech: '{text}'")
                    self.feedback.play_success()
                    break

                # Send text to conversation endpoint
                response = self.ai_client.send_conversation_text(
                    text=text,
                    session_id=session_id
                )

                if not response:
                    logger.warning("No response from conversation endpoint")
                    self.feedback.play_error()
                    continue

                status = response.get("status")
                message = response.get("message", "")

                if status == "error":
                    logger.warning(f"Conversation error: {message}")
                    self.feedback.play_error()
                    continue

                # Success - play response locally via TTS
                logger.info(f"Playing response via local TTS")
                self.feedback.speaking()

                # Get response text and play locally
                response_text = response.get("text", "")
                if response_text:
                    self.publish_status("speaking", response_text)
                    self.publish_message("response", response_text, session_id)
                    logger.info(f"Speaking: '{response_text[:50]}...'")
                    self.tts_service.speak(response_text)
                    logger.info("TTS playback complete")
                    self.feedback.play_success()

                # Update activity timestamp AFTER TTS completes
                # This ensures timeout measures "idle time" not "processing time"
                last_activity = time.time()

        except Exception as e:
            logger.error(f"Error in conversation loop: {e}")
        finally:
            # Clear flags to prevent auto-restart
            self.conversation_start_requested = False
            self.conversation_stop_requested = False

            # End conversation session
            self.ai_client.end_conversation(session_id)
            logger.info(f"Conversation ended (session={session_id})")
            self.publish_status("idle", "Conversation ended")
            self.feedback.idle()

            # Notify HA to turn off the conversation_mode toggle
            if self.mqtt_client:
                try:
                    self.mqtt_client.publish("voice_assistant/conversation_ended", "true")
                    logger.info("Published conversation_ended to MQTT")
                except Exception as e:
                    logger.warning(f"Failed to publish conversation_ended: {e}")

    def process_wake_word_detection(self):
        """Handle wake-word detection using unified session flow.

        Uses run_session() with the current conversation_mode_enabled setting.
        This ensures the toggle in the dashboard is respected.
        """
        logger.info("Wake word detected!")

        # Generate session ID and use current conversation mode setting
        session_id = str(uuid.uuid4())[:8]
        mode_str = "conversation" if self.conversation_mode_enabled else "single"
        logger.info(f"Starting {mode_str} mode session (id={session_id})")

        # Run unified session (handles feedback, state, MQTT, TTS)
        self.run_session(session_id, self.conversation_mode_enabled)

        # Reset audio stream after session
        self._reset_audio_stream()

    def run(self):
        """Main detection loop"""
        logger.info("Starting wake-word detection loop")
        self.running = True
        chunk_count = 0
        log_interval = 100  # Log every 100 chunks

        try:
            self.audio_capture.start()
            logger.info("Audio capture started - listening for wake word...")

            # Warmup period to stabilize audio stream and detector
            warmup_chunks = 50  # ~4 seconds at 80ms per chunk
            logger.info(f"Warming up detector ({warmup_chunks} chunks)...")
            for _ in range(warmup_chunks):
                audio_chunk = self.audio_capture.get_chunk()
                if audio_chunk is not None:
                    self.detector.predict(audio_chunk)  # Run prediction but ignore result
            # Note: Don't reset detector after warmup - it clears necessary model state
            logger.info("Warmup complete - ready for detection")

            while self.running:
                # Check for external trigger (MQTT command)
                if self.conversation_start_requested:
                    # Only respond to commands for MY room (device ownership check)
                    if self._session_room_id == self.room_id:
                        logger.info(f"MQTT session trigger for my room '{self.room_id}'")
                        self.conversation_start_requested = False  # Clear flag

                        # Start session via MQTT (uses current conversation_mode_enabled setting)
                        session_id = str(uuid.uuid4())[:8]
                        mode = "conversation" if self.conversation_mode_enabled else "single"
                        logger.info(f"Starting {mode} session (id={session_id})")

                        self.run_session(session_id, self.conversation_mode_enabled)

                        # Reset audio stream
                        self._reset_audio_stream()
                        chunk_count = 0
                    else:
                        logger.info(f"Ignoring MQTT command for room '{self._session_room_id}' (my room: '{self.room_id}')")
                        self.conversation_start_requested = False  # Clear flag
                    continue

                # Get audio chunk
                audio_chunk = self.audio_capture.get_chunk()

                if audio_chunk is None:
                    continue

                chunk_count += 1

                # Run wake-word detection
                prediction = self.detector.predict(audio_chunk)

                # Periodic debug logging
                if chunk_count % log_interval == 0:
                    logger.info(f"Processing chunks... (count: {chunk_count}, last prediction: {prediction:.4f})")

                if prediction >= self.detection_threshold:
                    logger.info(f"Wake word detected with confidence: {prediction:.2f}")

                    # Generate session ID and run session
                    # Mode is determined by conversation_mode_enabled flag
                    session_id = str(uuid.uuid4())[:8]
                    self.run_session(session_id, self.conversation_mode_enabled)

                    # Reset audio stream after session
                    self._reset_audio_stream()
                    chunk_count = 0

        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Error in detection loop: {e}")
            raise
        finally:
            self.shutdown()

    def _reset_audio_stream(self) -> None:
        """Reset audio capture stream after a session.

        Stops and restarts the audio stream and resets the detector state.
        """
        logger.info("Resetting audio capture stream...")
        self.audio_capture.stop()
        time.sleep(0.5)
        self.audio_capture._initialize()
        self.audio_capture.start()
        self.detector.reset()
        logger.info("Audio capture stream reset complete")
        time.sleep(1.0)  # Pause to avoid re-triggering from residual audio

    def shutdown(self):
        """Clean shutdown"""
        logger.info("Shutting down Wake-Word Detection Service")
        self.running = False

        # End any active session
        if self.state_machine:
            self.state_machine.reset()

        if self.tts_queue:
            self.tts_queue.stop()

        if self.parallel_stt:
            self.parallel_stt.shutdown()

        if self.audio_capture:
            self.audio_capture.stop()

        if self.feedback:
            self.feedback.cleanup()

        # Disconnect MQTT
        if self.mqtt_client:
            try:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            except Exception:
                pass

        logger.info("Shutdown complete")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    sys.exit(0)


def main():
    """Main entry point"""
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Setup model symlinks before initializing service
    setup_model_symlinks()

    # Create and run service
    service = WakeWordService()

    try:
        service.setup()
        service.run()
    except Exception as e:
        logger.error(f"Service failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
