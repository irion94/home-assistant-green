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
        self.tts_service: Optional[TTSService] = None
        self.tts_queue: Optional[TTSQueue] = None
        self.interrupt_listener: Optional[InterruptListener] = None
        self.mqtt_client: Optional[mqtt.Client] = None

        # MQTT command flags
        self.conversation_start_requested = False
        self.conversation_stop_requested = False

        # Conversation mode configuration
        # Default to single-command mode (false = one command then close)
        self.conversation_mode_enabled = os.getenv("CONVERSATION_MODE_DEFAULT", "false").lower() == "true"

        # Room identification for multi-device support
        self.room_id = os.getenv("ROOM_ID", "default")

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

            # Initialize parallel STT (Vosk + Whisper) for local speech-to-text
            vosk_model_path = os.getenv("VOSK_MODEL_PATH")
            whisper_model_size = os.getenv("WHISPER_MODEL_SIZE", "base")
            self.parallel_stt = ParallelSTT(
                vosk_model_path=vosk_model_path,
                whisper_model_size=whisper_model_size
            )
            logger.info(f"Parallel STT initialized (Vosk + Whisper {whisper_model_size})")

            # Initialize TTS service for local text-to-speech
            self.tts_service = TTSService()
            logger.info("TTS service initialized for local speech output")

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
                # Subscribe to room-scoped topics
                self.mqtt_client.subscribe(f"voice_assistant/room/{self.room_id}/command/#")
                self.mqtt_client.subscribe(f"voice_assistant/room/{self.room_id}/config/conversation_mode")
                # Also subscribe to legacy topics for backward compatibility during migration
                self.mqtt_client.subscribe("voice_assistant/command")
                self.mqtt_client.subscribe("voice_assistant/config/conversation_mode")
                self.mqtt_client.loop_start()
                logger.info(f"MQTT client connected to {mqtt_host}:{mqtt_port}")
                logger.info(f"Room ID: {self.room_id}")
                logger.info(f"Subscribed to room-scoped topics: voice_assistant/room/{self.room_id}/...")
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
        """Publish session state to room-scoped MQTT topics.

        New topic structure:
        - voice_assistant/room/{room_id}/session/active -> session_id or "none"
        - voice_assistant/room/{room_id}/session/{session_id}/state -> status string
        """
        if not self.mqtt_client:
            return

        try:
            base_topic = f"voice_assistant/room/{self.room_id}"

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
                    "room_id": self.room_id,
                    "timestamp": time.time()
                })

                # Legacy topic (backward compatibility)
                self.mqtt_client.publish(f"voice_assistant/{msg_type}", message_data)

                # Room-scoped topic (new format)
                if session_id:
                    self.mqtt_client.publish(
                        f"voice_assistant/room/{self.room_id}/session/{session_id}/{msg_type}",
                        message_data
                    )

                logger.info(f"Published MQTT {msg_type}: '{text[:50]}...' to session {session_id}")
            except Exception as e:
                logger.warning(f"Failed to publish MQTT message: {e}")

    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT commands.

        Handles both legacy and room-scoped topics:
        - Legacy: voice_assistant/command, voice_assistant/config/conversation_mode
        - Room-scoped: voice_assistant/room/{room_id}/command/*, voice_assistant/room/{room_id}/config/*
        """
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            logger.info(f"MQTT message received: {topic} = {payload}")

            # Room-scoped command topics
            room_prefix = f"voice_assistant/room/{self.room_id}"
            if topic.startswith(f"{room_prefix}/command/"):
                command = topic.split("/")[-1]  # Get last part: start, stop
                self._handle_command(command, payload)
            elif topic == f"{room_prefix}/config/conversation_mode":
                self._handle_conversation_mode_change(payload)

            # Legacy topics (backward compatibility)
            elif topic == "voice_assistant/command":
                if payload == "start_conversation":
                    self._handle_command("start", "")
                elif payload == "stop_conversation":
                    self._handle_command("stop", "")
            elif topic == "voice_assistant/config/conversation_mode":
                self._handle_conversation_mode_change(payload)

        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def _handle_command(self, command: str, payload: str) -> None:
        """Handle voice assistant commands.

        Args:
            command: 'start' or 'stop'
            payload: Optional JSON payload with mode, source info
        """
        if command == "start":
            logger.info("MQTT command: start session")
            self.conversation_start_requested = True
            self.conversation_stop_requested = False
            # Parse payload for mode if provided
            if payload:
                try:
                    data = json.loads(payload)
                    if "mode" in data:
                        self.conversation_mode_enabled = data["mode"] == "multi"
                        logger.info(f"Session mode set to: {'multi-turn' if self.conversation_mode_enabled else 'single'}")
                        # Publish mode change back to dashboard for UI update
                        if self.mqtt_client:
                            self.mqtt_client.publish(
                                f"voice_assistant/room/{self.room_id}/config/conversation_mode",
                                "true" if self.conversation_mode_enabled else "false",
                                retain=True
                            )
                            logger.info(f"Published conversation mode: {self.conversation_mode_enabled}")
                except json.JSONDecodeError:
                    pass
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
                    f"voice_assistant/room/{self.room_id}/config/conversation_mode",
                    "true" if enabled else "false",
                    retain=True
                )

    def process_interaction(self, session_id: str) -> InteractionResult:
        """Process a single voice interaction.

        Unified method that handles one complete interaction cycle:
        1. Record audio (LISTENING state)
        2. Transcribe speech (TRANSCRIBING state)
        3. Get LLM response (PROCESSING state)
        4. Play TTS response (SPEAKING state)

        Args:
            session_id: Session identifier

        Returns:
            InteractionResult with transcript, response, and flags
        """
        result = InteractionResult()

        try:
            # LISTENING - Record user speech
            self.state_machine.transition(VoiceState.LISTENING)
            self.feedback.play_listening()
            logger.info("Listening for speech...")

            audio_data = self.audio_capture.record(
                duration=self.recording_duration,
                stop_check=lambda: self.conversation_stop_requested
            )

            # Check for stop during recording
            if self.conversation_stop_requested:
                result.should_continue = False
                return result

            logger.info(f"Recorded {len(audio_data)} audio frames")

            # TRANSCRIBING - Convert speech to text
            self.state_machine.transition(VoiceState.TRANSCRIBING)
            self.feedback.processing()

            stt_start = time.time()
            stt_result = self.parallel_stt.transcribe_parallel(audio_data, self.sample_rate)
            result.stt_duration = time.time() - stt_start
            result.transcript = stt_result.selected.text
            result.stt_engine = stt_result.selected.engine

            # Publish STT comparison for debugging
            self._publish_stt_comparison(stt_result, session_id)

            if not result.transcript:
                logger.info("No speech detected")
                result.should_continue = True  # Continue listening in multi-turn
                return result

            logger.info(f"Transcribed: '{result.transcript}' (via {result.stt_engine})")
            self.publish_message("transcript", result.transcript, session_id)

            # Check for end command keywords
            result.is_end_command = self._is_end_command(result.transcript)
            if result.is_end_command:
                logger.info(f"End command detected: '{result.transcript}'")
                result.should_continue = False
                return result

            # PROCESSING - Get LLM response
            self.state_machine.transition(VoiceState.PROCESSING)

            llm_start = time.time()
            response = self.ai_client.send_conversation_text(
                text=result.transcript,
                session_id=session_id
            )
            result.llm_duration = time.time() - llm_start

            if not response:
                logger.warning("No response from AI Gateway")
                result.error = "No response from AI Gateway"
                self.feedback.play_error()
                return result

            if response.get("status") == "error":
                result.error = response.get("message", "Unknown error")
                logger.warning(f"AI Gateway error: {result.error}")
                self.feedback.play_error()
                return result

            result.response = response.get("text", "")

            # Check for conversation mode action from AI
            action = response.get("action")
            if action == "conversation_start":
                logger.info("AI triggered conversation mode")
                self.conversation_mode_enabled = True
                # Publish mode change to MQTT
                self.mqtt_client.publish(
                    f"voice_assistant/room/{self.room_id}/config/conversation_mode",
                    "true",
                    retain=True
                )
                result.should_continue = True  # Continue in conversation mode
            elif action == "conversation_end":
                logger.info("AI ended conversation mode")
                self.conversation_mode_enabled = False
                self.mqtt_client.publish(
                    f"voice_assistant/room/{self.room_id}/config/conversation_mode",
                    "false",
                    retain=True
                )
                result.should_continue = False

            # SPEAKING - Play TTS response
            if result.response:
                self.state_machine.transition(VoiceState.SPEAKING)
                self.feedback.speaking()
                self.publish_message("response", result.response, session_id)

                tts_start = time.time()
                logger.info(f"Speaking: '{result.response[:50]}...'")
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
        return any(keyword in text_lower for keyword in end_keywords)

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
                    f"voice_assistant/room/{self.room_id}/session/{session_id}/ended",
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
                    logger.info("MQTT session trigger detected")
                    self.conversation_start_requested = False  # Clear flag

                    # Start session via MQTT (uses current conversation_mode_enabled setting)
                    session_id = str(uuid.uuid4())[:8]
                    self.run_session(session_id, self.conversation_mode_enabled)

                    # Reset audio stream
                    self._reset_audio_stream()
                    chunk_count = 0
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
