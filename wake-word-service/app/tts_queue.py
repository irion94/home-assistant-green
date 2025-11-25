"""Parallel TTS synthesis queue for reduced latency.

This module implements a background synthesis queue that allows TTS audio
to be synthesized in parallel while previous chunks are playing, reducing
the latency from first LLM token to first heard audio.
"""

from __future__ import annotations

import logging
import os
import queue
import subprocess
import tempfile
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Optional

logger = logging.getLogger(__name__)


class ParallelTTSQueue:
    """Parallel TTS synthesis queue using ThreadPoolExecutor.

    This class manages background XTTS synthesis while the main thread
    plays audio via aplay, enabling pipeline parallelism to reduce latency.

    Architecture:
    - Main thread: Calls enqueue() as sentences arrive from streaming LLM
    - Background threads: Synthesize XTTS audio (2-4s per sentence)
    - Main thread: Calls play_next() to wait for synthesis → play via aplay

    Example flow:
        Time 0s:   enqueue(sentence1) → Background: Start synthesis
        Time 1s:   enqueue(sentence2) → Background: Start synthesis
        Time 3s:   play_next() → Sentence 1 synthesis done, play via aplay
        Time 5s:   play_next() → Sentence 2 already done, play immediately
    """

    def __init__(self, tts_service, max_workers: int = 2):
        """Initialize parallel TTS queue.

        Args:
            tts_service: TTSService instance for XTTS synthesis
            max_workers: Number of background synthesis threads (1-2 recommended)
        """
        self.tts_service = tts_service
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.queue: queue.Queue[tuple[str, Future[bytes], str]] = queue.Queue()
        self.interrupted = False
        self.current_process: Optional[subprocess.Popen] = None

        logger.info(f"ParallelTTSQueue initialized with {max_workers} worker(s)")

    def enqueue(self, text: str, language: str = "pl") -> None:
        """Submit text for background XTTS synthesis (non-blocking).

        This method returns immediately. Synthesis happens in the
        background thread pool.

        Args:
            text: Text to synthesize
            language: Language code ('pl' or 'en')
        """
        # Reset interrupted flag when enqueueing new content
        self.interrupted = False

        # Submit synthesis task to thread pool
        future = self.executor.submit(self._synthesize, text, language)
        self.queue.put((text, future, language))

        logger.debug(f"Enqueued for synthesis: '{text[:40]}...' (queue depth: {self.queue.qsize()})")

    def _synthesize(self, text: str, language: str) -> bytes:
        """Background synthesis worker (runs in thread pool).

        This method is called by ThreadPoolExecutor workers.

        Args:
            text: Text to synthesize
            language: Language code

        Returns:
            WAV audio bytes

        Raises:
            Exception: If XTTS synthesis fails
        """
        start = time.time()

        try:
            # Call XTTS synthesis method from TTS service
            wav_bytes = self.tts_service._synthesize_xtts(text, language)
            duration = time.time() - start

            logger.info(
                f"XTTS synthesis complete: {duration:.2f}s for "
                f"{len(text)} chars ('{text[:30]}...')"
            )

            return wav_bytes

        except Exception as e:
            duration = time.time() - start
            logger.error(f"XTTS synthesis failed after {duration:.2f}s: {e}")
            raise

    def play_next(self, timeout: float = 10.0) -> bool:
        """Wait for next audio chunk synthesis, then play via aplay.

        This method blocks until:
        1. Background synthesis completes (waiting for Future)
        2. aplay playback completes (subprocess blocks)

        Args:
            timeout: Maximum wait time for synthesis (seconds)

        Returns:
            True if audio was played successfully
            False if queue empty, interrupted, timeout, or error
        """
        try:
            # Get next item from queue (blocks if empty)
            text, future, lang = self.queue.get(timeout=timeout)

            # Wait for background synthesis to complete
            try:
                wav_bytes = future.result(timeout=timeout)
            except TimeoutError:
                logger.warning(
                    f"Synthesis timeout ({timeout}s) for: '{text[:30]}...'"
                )
                return False
            except Exception as e:
                logger.error(f"Synthesis error for '{text[:30]}...': {e}")
                return False

            # Check interrupt flag before playing
            if self.interrupted:
                logger.info("Playback interrupted before starting")
                return False

            # Play audio via aplay (blocking)
            self._play_audio(wav_bytes, text)
            return True

        except queue.Empty:
            logger.debug("Queue empty, no more audio to play")
            return False
        except Exception as e:
            logger.error(f"Error in play_next: {e}", exc_info=True)
            return False

    def _play_audio(self, wav_bytes: bytes, text: str) -> None:
        """Play audio via aplay (blocks until playback complete).

        This method uses the same playback pattern as TTSService.speak(),
        with interrupt support via self.current_process.

        Args:
            wav_bytes: WAV audio data
            text: Original text (for logging only)

        Raises:
            Exception: If aplay fails or timeout occurs
        """
        # Write audio to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_bytes)
            tmp_path = tmp.name

        try:
            logger.info(
                f"Playing audio: '{text[:40]}...' "
                f"({len(wav_bytes)} bytes, device={self.tts_service.output_device})"
            )

            # Start aplay subprocess (store for interrupt handling)
            self.current_process = subprocess.Popen(
                ["aplay", "-D", self.tts_service.output_device, "-q", tmp_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )

            # Wait for playback to complete
            try:
                self.current_process.wait(timeout=120)  # XTTS can generate long audio

                if self.current_process.returncode != 0:
                    stderr = self.current_process.stderr.read() if self.current_process.stderr else b""
                    logger.error(f"aplay failed (code {self.current_process.returncode}): {stderr.decode()}")

            except subprocess.TimeoutExpired:
                logger.error("aplay timeout (120s), killing process")
                self.current_process.kill()
                self.current_process.wait()  # Clean up zombie

        finally:
            # Clean up
            self.current_process = None
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def interrupt(self) -> None:
        """Immediately stop current playback and cancel all pending synthesis.

        This method:
        1. Sets interrupt flag (prevents new playback)
        2. Kills current aplay process
        3. Cancels all pending synthesis futures
        4. Clears the queue
        """
        logger.info("Interrupting TTS queue (stop playback + cancel pending)")
        self.interrupted = True

        # Kill current aplay process
        if self.current_process:
            try:
                logger.debug("Killing current aplay process")
                self.current_process.kill()
                self.current_process.wait(timeout=1.0)  # Wait for process to die
            except subprocess.TimeoutExpired:
                logger.warning("aplay process did not die after kill signal")
            except Exception as e:
                logger.error(f"Error killing aplay process: {e}")
            finally:
                self.current_process = None

        # Cancel all pending synthesis futures
        cancelled_count = 0
        while not self.queue.empty():
            try:
                text, future, lang = self.queue.get_nowait()

                # Try to cancel the future (only works if not started yet)
                if future.cancel():
                    logger.debug(f"Cancelled pending synthesis: '{text[:30]}...'")
                    cancelled_count += 1
                else:
                    # Future already running or done - can't cancel
                    logger.debug(f"Could not cancel synthesis (already running): '{text[:30]}...'")

            except queue.Empty:
                break
            except Exception as e:
                logger.error(f"Error cancelling synthesis: {e}")

        if cancelled_count > 0:
            logger.info(f"Cancelled {cancelled_count} pending synthesis task(s)")

    def clear(self) -> None:
        """Alias for interrupt() for consistency with other queue interfaces."""
        self.interrupt()

    def has_pending(self) -> bool:
        """Check if queue has pending audio chunks.

        Returns:
            True if queue is not empty (more audio to play)
        """
        return not self.queue.empty()

    def get_depth(self) -> int:
        """Get current queue depth for monitoring/debugging.

        Returns:
            Number of pending chunks in queue
        """
        return self.queue.qsize()

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown thread pool executor.

        Call this when done using the queue to clean up resources.

        Args:
            wait: If True, wait for pending futures to complete
        """
        logger.info(f"Shutting down ParallelTTSQueue (wait={wait})")

        # Interrupt any current playback
        self.interrupt()

        # Shutdown thread pool
        self.executor.shutdown(wait=wait)

        logger.info("ParallelTTSQueue shutdown complete")
