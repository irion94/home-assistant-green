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

from detector import WakeWordDetector
from audio_capture import AudioCapture
from ai_gateway_client import AIGatewayClient
from feedback import AudioFeedback
from transcriber import Transcriber
from tts_service import TTSService

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
        self.transcriber: Optional[Transcriber] = None
        self.tts_service: Optional[TTSService] = None
        self.tts_queue: Optional[TTSQueue] = None
        self.interrupt_listener: Optional[InterruptListener] = None

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

            # Initialize transcriber for local speech-to-text
            vosk_model_path = os.getenv("VOSK_MODEL_PATH")
            self.transcriber = Transcriber(model_path=vosk_model_path)
            logger.info("Transcriber initialized for local STT")

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

                # Transcribe locally
                text = self.transcriber.transcribe(audio_data, self.sample_rate)
                if not text:
                    logger.info("No speech detected, continuing conversation...")
                    continue

                logger.info(f"Transcribed: '{text}'")

                # Check for conversation end keywords in user's speech BEFORE sending
                text_lower = text.lower()
                end_keywords = ["stop", "koniec", "wystarczy", "to wszystko", "bye", "goodbye", "end conversation", "zakończ"]
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

                # Update activity timestamp
                last_activity = time.time()

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
                    logger.info(f"Speaking: '{response_text[:50]}...'")
                    self.tts_service.speak(response_text)
                    logger.info("TTS playback complete")
                    self.feedback.play_success()

        except Exception as e:
            logger.error(f"Error in conversation loop: {e}")
        finally:
            # End conversation session
            self.ai_client.end_conversation(session_id)
            logger.info(f"Conversation ended (session={session_id})")
            self.feedback.idle()

    def process_wake_word_detection(self):
        """Handle wake-word detection event with streaming TTS"""
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

            # Save audio to temp file for streaming upload
            import tempfile
            import wave
            import numpy as np

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
                # Convert audio frames to WAV
                audio_array = np.array(audio_data, dtype=np.int16)
                with wave.open(temp_path, 'wb') as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(self.sample_rate)
                    wav_file.writeframes(audio_array.tobytes())

            logger.info(f"Saved audio to temp file: {temp_path}")

            # Send to streaming endpoint
            ai_gateway_url = os.getenv("AI_GATEWAY_URL", "http://host.docker.internal:8080")
            stream_url = f"{ai_gateway_url}/voice/stream"
            logger.info(f"Streaming request to {stream_url}")

            conversation_start = False
            sentence_count = 0
            transcription = None

            try:
                with open(temp_path, 'rb') as audio_file:
                    files = {'audio': ('recording.wav', audio_file, 'audio/wav')}

                    with httpx.Client(timeout=60.0) as client:
                        with client.stream('POST', stream_url, files=files) as response:
                            response.raise_for_status()

                            for line in response.iter_lines():
                                if not line:
                                    continue

                                if line.startswith('data: '):
                                    data_str = line[6:]  # Remove 'data: ' prefix

                                    if data_str == '[DONE]':
                                        logger.info(f"Streaming complete: {sentence_count} sentences")
                                        break

                                    try:
                                        data = json.loads(data_str)

                                        # Handle transcription
                                        if 'transcription' in data:
                                            transcription = data['transcription']
                                            logger.info(f"Transcribed: '{transcription}'")

                                        # Handle errors
                                        if 'error' in data:
                                            logger.warning(f"Stream error: {data['error']}")
                                            self.tts_queue.add(data['error'])
                                            break

                                        # Handle sentences
                                        if 'sentence' in data:
                                            sentence = data['sentence']
                                            sentence_count += 1

                                            # Check for conversation mode
                                            if data.get('action') == 'conversation_start':
                                                conversation_start = True

                                            # Queue sentence for immediate TTS playback
                                            logger.info(f"Queueing sentence {sentence_count}: {sentence[:50]}...")
                                            self.tts_queue.add(sentence)

                                            # Show speaking LED on first sentence
                                            if sentence_count == 1:
                                                self.feedback.speaking()

                                    except json.JSONDecodeError as e:
                                        logger.warning(f"JSON decode error: {e}, data: {data_str}")
                                        continue

            except httpx.HTTPError as e:
                logger.error(f"HTTP error during streaming: {e}")
                self.feedback.play_error()
                self.tts_service.speak("Błąd połączenia z serwerem")
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass

            # Start interrupt listener while TTS plays
            if sentence_count > 0:
                self.interrupt_listener.start()

            # Wait for TTS with interrupt checking
            logger.info("Waiting for TTS queue to complete (interrupt enabled)...")
            while not self.tts_queue.queue.empty() or self.tts_queue.playing:
                # Check for interrupt
                if self.interrupt_listener.was_interrupted():
                    logger.info("User interrupted TTS playback")
                    self.tts_queue.clear()
                    self.feedback.idle()
                    break
                time.sleep(0.1)

            # Stop interrupt listener
            self.interrupt_listener.stop()
            logger.info("TTS playback complete")

            # Show success LED after all TTS completes (unless interrupted)
            if sentence_count > 0 and not self.interrupt_listener.was_interrupted():
                self.feedback.play_success()

            # Handle conversation mode
            if conversation_start:
                logger.info("Entering conversation mode...")

                # Reset audio stream for conversation
                self.audio_capture.stop()
                time.sleep(0.5)
                self.audio_capture._initialize()
                self.audio_capture.start()

                # Run conversation loop
                session_id = str(uuid.uuid4())
                self.run_conversation_loop(session_id)

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

        if self.tts_queue:
            self.tts_queue.stop()

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
