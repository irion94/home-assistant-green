"""
Audio Capture Module
Handles audio input from ReSpeaker 4 Mic Array
"""

import logging
import numpy as np
import pyaudio
from typing import Optional
from collections import deque

logger = logging.getLogger(__name__)


class AudioCapture:
    """Audio capture from microphone"""

    def __init__(
        self,
        device: str = "hw:2,0",
        sample_rate: int = 16000,
        channels: int = 6,
        chunk_size: int = 1280
    ):
        """
        Initialize audio capture

        Args:
            device: ALSA device name (e.g., "hw:2,0")
            sample_rate: Sample rate in Hz
            channels: Number of audio channels
            chunk_size: Number of frames per buffer
        """
        self.device = device
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size

        self.pyaudio = None
        self.stream = None
        self.buffer = deque(maxlen=100)  # Circular buffer for recent audio

        self._initialize()

    def _initialize(self):
        """Initialize PyAudio"""
        logger.info("Initializing PyAudio")

        try:
            self.pyaudio = pyaudio.PyAudio()

            # Find device index by name
            device_index = self._find_device_index()

            if device_index is None:
                raise ValueError(f"Audio device not found: {self.device}")

            logger.info(f"Found audio device at index {device_index}")

        except Exception as e:
            logger.error(f"Failed to initialize PyAudio: {e}")
            raise

    def _find_device_index(self) -> Optional[int]:
        """Find ALSA device index"""
        found_device = None

        for i in range(self.pyaudio.get_device_count()):
            info = self.pyaudio.get_device_info_by_index(i)
            name = info.get("name", "")
            max_input = info.get("maxInputChannels", 0)

            logger.debug(f"Device {i}: {name}, input channels: {max_input}")

            # Match by device name
            if "ReSpeaker" in name or self.device in name:
                found_device = i
                # Prefer device with input channels if available
                if max_input > 0:
                    logger.info(f"Found capture device: {name} with {max_input} input channels")
                    return i

        # If we found a device but it reported 0 input channels, use it anyway
        # (PyAudio sometimes reports wrong capabilities for ALSA devices)
        if found_device is not None:
            logger.warning(f"Device {found_device} reports 0 input channels, attempting to use anyway")
            return found_device

        return None

    def start(self):
        """Start audio capture stream"""
        logger.info("Starting audio capture stream")

        try:
            device_index = self._find_device_index()

            logger.info(f"Opening stream: device={device_index}, channels={self.channels}, rate={self.sample_rate}, chunk={self.chunk_size}")

            self.stream = self.pyaudio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=self.chunk_size,
                stream_callback=None  # Blocking mode
            )

            logger.info("Audio stream started successfully")

        except Exception as e:
            logger.error(f"Failed to start audio stream: {e}")
            logger.error(f"Device info: {self.pyaudio.get_device_info_by_index(device_index) if device_index is not None else 'None'}")
            raise

    def stop(self):
        """Stop audio capture stream"""
        logger.info("Stopping audio capture")

        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

        if self.pyaudio:
            self.pyaudio.terminate()
            self.pyaudio = None

    def get_chunk(self) -> Optional[np.ndarray]:
        """
        Get single audio chunk

        Returns:
            Numpy array with audio data (mono, int16) or None on error
        """
        if not self.stream or not self.stream.is_active():
            return None

        try:
            # Read audio data
            data = self.stream.read(self.chunk_size, exception_on_overflow=False)

            # Convert bytes to numpy array
            audio = np.frombuffer(data, dtype=np.int16)

            # Reshape to separate channels
            audio = audio.reshape(-1, self.channels)

            # Use first channel (or average channels) for mono
            audio_mono = audio[:, 0]  # Channel 0

            # Apply software gain boost (ReSpeaker has low output levels)
            # Note: 16x caused clipping distortion, reduced to 8x
            gain = 8.0  # Boost by 8x for better sensitivity without clipping
            audio_mono = np.clip(audio_mono.astype(np.float32) * gain, -32768, 32767).astype(np.int16)

            # Debug: log audio stats periodically
            if len(self.buffer) % 100 == 0:
                max_val = np.max(np.abs(audio_mono))
                mean_val = np.mean(np.abs(audio_mono))
                logger.debug(f"Audio stats: max={max_val}, mean={mean_val:.1f}, samples={len(audio_mono)}")

            # Store in buffer for recording
            self.buffer.append(audio_mono.copy())

            return audio_mono

        except Exception as e:
            logger.error(f"Error reading audio chunk: {e}")
            return None

    def record(self, duration: float) -> np.ndarray:
        """
        Record audio with voice activity detection (VAD)

        Stops recording after silence is detected or max duration reached.

        Args:
            duration: Maximum recording duration in seconds

        Returns:
            Numpy array with recorded audio (mono, int16)
        """
        logger.info(f"Recording (max {duration}s, VAD enabled)")

        max_chunks = int(duration * self.sample_rate / self.chunk_size)
        recorded_chunks = []

        # VAD parameters - tuned for faster cutoff
        silence_threshold = 1000  # Audio level below this is considered silence (lowered for sensitivity)
        silence_chunks_to_stop = 10  # ~0.8 seconds of silence to stop (reduced from 15)
        min_speech_chunks = 5  # Minimum ~0.4 seconds of speech before allowing stop

        consecutive_silence = 0
        speech_detected = False
        speech_chunks = 0

        try:
            for i in range(max_chunks):
                chunk = self.get_chunk()
                if chunk is None:
                    continue

                recorded_chunks.append(chunk)

                # Calculate audio energy
                energy = np.mean(np.abs(chunk))

                if energy > silence_threshold:
                    # Speech detected
                    speech_detected = True
                    speech_chunks += 1
                    consecutive_silence = 0
                else:
                    # Silence
                    consecutive_silence += 1

                # Stop if we've had speech and now have enough silence
                if speech_detected and speech_chunks >= min_speech_chunks:
                    if consecutive_silence >= silence_chunks_to_stop:
                        logger.info(f"VAD: Speech ended after {len(recorded_chunks)} chunks")
                        break

            # Concatenate all chunks
            if recorded_chunks:
                audio = np.concatenate(recorded_chunks)
                logger.info(f"Recorded {len(audio)} samples ({len(audio)/self.sample_rate:.2f}s)")
                return audio
            else:
                logger.warning("No audio data recorded")
                return np.array([], dtype=np.int16)

        except Exception as e:
            logger.error(f"Error during recording: {e}")
            return np.array([], dtype=np.int16)

    def get_device_info(self) -> dict:
        """Get information about the audio device"""
        device_index = self._find_device_index()

        if device_index is None:
            return {}

        return self.pyaudio.get_device_info_by_index(device_index)
