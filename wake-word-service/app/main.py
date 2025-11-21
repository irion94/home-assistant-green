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
from typing import Optional
from pathlib import Path

from detector import WakeWordDetector
from audio_capture import AudioCapture
from ai_gateway_client import AIGatewayClient
from feedback import AudioFeedback

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='{"timestamp": "%(asctime)s", "logger": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)


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

        except Exception as e:
            logger.error(f"Failed to initialize service: {e}")
            raise

    def run_conversation_loop(self, session_id: str):
        """Run continuous conversation loop until exit or timeout.

        Args:
            session_id: Unique session identifier
        """
        logger.info(f"Starting conversation mode (session={session_id}, timeout={self.conversation_timeout}s)")
        last_activity = time.time()

        try:
            while self.running:
                # Check timeout
                if time.time() - last_activity > self.conversation_timeout:
                    logger.info("Conversation timeout reached")
                    break

                # Show listening LED
                self.feedback.play_listening()

                # Record user speech
                logger.info("Listening for conversation input...")
                audio_data = self.audio_capture.record(duration=self.recording_duration)
                logger.info(f"Recorded {len(audio_data)} audio frames")

                # Show processing LED
                self.feedback.processing()

                # Send to conversation endpoint
                response = self.ai_client.send_conversation_voice(
                    audio_data=audio_data,
                    sample_rate=self.sample_rate,
                    session_id=session_id
                )

                if not response:
                    logger.warning("No response from conversation endpoint")
                    self.feedback.play_error()
                    continue

                # Update activity timestamp
                last_activity = time.time()

                status = response.get("status")
                message = response.get("message", "")

                if status == "error":
                    # Check if it's a silence/no speech error
                    if "could not understand" in message.lower():
                        logger.info("No speech detected, continuing conversation...")
                        continue
                    else:
                        logger.warning(f"Conversation error: {message}")
                        self.feedback.play_error()
                        continue

                # Check for conversation end keywords in the message
                # Message format is "Response to: 'transcribed text'"
                message_lower = message.lower()
                end_keywords = ["stop", "koniec", "wystarczy", "to wszystko", "bye", "goodbye", "end conversation"]
                should_end = any(keyword in message_lower for keyword in end_keywords)

                if should_end:
                    logger.info("Conversation end keyword detected")
                    self.feedback.play_success()
                    break

                # Success - response was sent to TTS
                logger.info(f"Conversation response sent to TTS")
                self.feedback.play_success()

                # Wait for TTS to finish, but listen for interrupt commands
                # TTS speed is 1.2x, so adjust duration: ~180 words per minute = ~3 words per second
                response_text = response.get("text", "")
                word_count = len(response_text.split()) if response_text else 0
                tts_duration = max(2.0, word_count / 3.0 + 0.5)  # Faster TTS = shorter wait
                logger.info(f"TTS playing ({word_count} words, ~{tts_duration:.1f}s). Listening for interrupt...")

                # Listen for interrupt during TTS playback
                interrupt_keywords = ["przerwij", "stop", "cancel", "anuluj", "czekaj", "wait"]
                interrupt_detected = False
                start_time = time.time()

                while time.time() - start_time < tts_duration:
                    # Record short audio for interrupt detection (2 seconds)
                    try:
                        short_audio = self.audio_capture.record(duration=2)
                        # Send for quick transcription
                        interrupt_response = self.ai_client.send_conversation_voice(
                            audio_data=short_audio,
                            sample_rate=self.sample_rate,
                            session_id=f"{session_id}_interrupt"
                        )
                        if interrupt_response:
                            interrupt_text = interrupt_response.get("message", "").lower()
                            if any(kw in interrupt_text for kw in interrupt_keywords):
                                logger.info(f"Interrupt detected: {interrupt_text}")
                                interrupt_detected = True
                                # Stop media playback
                                self.ai_client.stop_media()
                                break
                    except Exception as e:
                        logger.debug(f"Interrupt check failed: {e}")
                        time.sleep(1.0)

                if interrupt_detected:
                    logger.info("Conversation interrupted - ready for new input")
                    self.feedback.play_listening()

        except Exception as e:
            logger.error(f"Error in conversation loop: {e}")
        finally:
            # End conversation session
            self.ai_client.end_conversation(session_id)
            logger.info(f"Conversation ended (session={session_id})")
            self.feedback.idle()

    def process_wake_word_detection(self):
        """Handle wake-word detection event"""
        logger.info("Wake word detected!")

        # Play wake-word detected beep and show LED
        self.feedback.play_wake_detected()

        # Record audio for command
        logger.info(f"Recording command for {self.recording_duration} seconds...")
        try:
            # Show listening LED
            self.feedback.play_listening()

            audio_data = self.audio_capture.record(duration=self.recording_duration)
            logger.info(f"Recorded {len(audio_data)} audio frames")

            # Show processing LED
            self.feedback.processing()

            # Send to AI Gateway for processing
            logger.info("Sending audio to AI Gateway...")
            response = self.ai_client.process_voice_command(
                audio_data=audio_data,
                sample_rate=self.sample_rate
            )

            if response and response.get("status") == "success":
                logger.info(f"Command processed successfully: {response.get('message')}")

                # Check if conversation mode was requested
                plan = response.get("plan", {})
                action = plan.get("action") if plan else None

                if action == "conversation_start":
                    logger.info("Entering conversation mode...")
                    self.feedback.play_success()

                    # Reset audio stream for conversation
                    self.audio_capture.stop()
                    time.sleep(0.5)
                    self.audio_capture._initialize()
                    self.audio_capture.start()

                    # Run conversation loop
                    session_id = str(uuid.uuid4())
                    self.run_conversation_loop(session_id)
                else:
                    self.feedback.play_success()
            else:
                error_msg = response.get("message", "Unknown error") if response else "No response"
                logger.warning(f"Command processing failed: {error_msg}")
                self.feedback.play_error()

        except Exception as e:
            logger.error(f"Error processing voice command: {e}")
            self.feedback.play_error()
        finally:
            # Return to idle state
            self.feedback.idle()

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
                    self.process_wake_word_detection()

                    # Reset audio stream after command processing
                    # (stream can stall during long AI Gateway requests)
                    logger.info("Resetting audio capture stream...")
                    self.audio_capture.stop()
                    time.sleep(0.5)
                    self.audio_capture._initialize()
                    self.audio_capture.start()
                    logger.info("Audio capture stream reset complete")

                    # Reset detector state to clear prediction buffer
                    self.detector.reset()
                    logger.info("Detector state reset")

                    # Longer pause to avoid re-triggering from residual audio
                    time.sleep(2.0)
                    chunk_count = 0  # Reset counter after detection

        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Error in detection loop: {e}")
            raise
        finally:
            self.shutdown()

    def shutdown(self):
        """Clean shutdown"""
        logger.info("Shutting down Wake-Word Detection Service")
        self.running = False

        if self.audio_capture:
            self.audio_capture.stop()

        if self.feedback:
            self.feedback.cleanup()

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
