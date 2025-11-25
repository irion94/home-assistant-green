"""Voice Assistant State Machine.

Unified state management for wake-word detection and conversation flow.
This module provides a clean, testable state machine that handles all
voice assistant states and transitions.
"""

from __future__ import annotations

import logging
import time
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class VoiceState(Enum):
    """Voice assistant states.

    State flow:
        IDLE -> WAKE_DETECTED -> LISTENING -> TRANSCRIBING -> PROCESSING -> SPEAKING

    After SPEAKING:
        - Single mode: -> IDLE
        - Multi-turn mode: -> WAITING -> LISTENING (loop) or -> IDLE (on end/timeout)
    """
    IDLE = auto()           # Listening for wake-word only
    WAKE_DETECTED = auto()  # Wake word detected, preparing to record
    LISTENING = auto()      # Recording user speech
    TRANSCRIBING = auto()   # STT processing
    PROCESSING = auto()     # Waiting for LLM response
    SPEAKING = auto()       # TTS playback in progress
    WAITING = auto()        # Multi-turn: ready for next input (no wake-word needed)


# Valid state transitions
VALID_TRANSITIONS: dict[VoiceState, set[VoiceState]] = {
    VoiceState.IDLE: {VoiceState.WAKE_DETECTED},
    VoiceState.WAKE_DETECTED: {VoiceState.LISTENING, VoiceState.IDLE},
    VoiceState.LISTENING: {VoiceState.TRANSCRIBING, VoiceState.IDLE},
    VoiceState.TRANSCRIBING: {VoiceState.PROCESSING, VoiceState.IDLE, VoiceState.WAITING},
    VoiceState.PROCESSING: {VoiceState.SPEAKING, VoiceState.IDLE},
    VoiceState.SPEAKING: {VoiceState.IDLE, VoiceState.WAITING},
    VoiceState.WAITING: {VoiceState.LISTENING, VoiceState.IDLE},
}


@dataclass
class SessionContext:
    """Context for a voice session.

    Holds all session-related state including room_id, conversation mode,
    and timing information.
    """
    session_id: str
    room_id: str
    conversation_mode: bool = False  # True for multi-turn, False for single command
    created_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    turn_count: int = 0

    def touch(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = time.time()

    def increment_turn(self) -> None:
        """Increment turn count and touch activity."""
        self.turn_count += 1
        self.touch()


class VoiceStateMachine:
    """State machine for voice assistant flow.

    Manages state transitions and notifies listeners on state changes.
    Thread-safe for use in async/multi-threaded environments.
    """

    def __init__(
        self,
        room_id: str = "default",
        on_state_change: Optional[Callable[[VoiceState, VoiceState, Optional[SessionContext]], None]] = None
    ):
        """Initialize state machine.

        Args:
            room_id: Room identifier for this instance
            on_state_change: Callback for state transitions (old_state, new_state, session)
        """
        self._state = VoiceState.IDLE
        self._session: Optional[SessionContext] = None
        self._room_id = room_id
        self._on_state_change = on_state_change
        self._state_entered_at = time.time()

        logger.info(f"VoiceStateMachine initialized (room_id={room_id})")

    @property
    def state(self) -> VoiceState:
        """Current state."""
        return self._state

    @property
    def session(self) -> Optional[SessionContext]:
        """Current session context."""
        return self._session

    @property
    def room_id(self) -> str:
        """Room identifier."""
        return self._room_id

    @property
    def state_duration(self) -> float:
        """Time spent in current state (seconds)."""
        return time.time() - self._state_entered_at

    def can_transition(self, new_state: VoiceState) -> bool:
        """Check if transition to new_state is valid.

        Args:
            new_state: Target state

        Returns:
            True if transition is valid
        """
        valid_targets = VALID_TRANSITIONS.get(self._state, set())
        return new_state in valid_targets

    def transition(self, new_state: VoiceState, force: bool = False) -> bool:
        """Transition to a new state.

        Args:
            new_state: Target state
            force: If True, allow transition even if invalid (use for error recovery)

        Returns:
            True if transition succeeded
        """
        if not force and not self.can_transition(new_state):
            logger.warning(
                f"Invalid state transition: {self._state.name} -> {new_state.name}"
            )
            return False

        old_state = self._state
        self._state = new_state
        self._state_entered_at = time.time()

        logger.info(f"State transition: {old_state.name} -> {new_state.name}")

        # Notify listener
        if self._on_state_change:
            try:
                self._on_state_change(old_state, new_state, self._session)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")

        return True

    def start_session(self, session_id: str, conversation_mode: bool = False) -> SessionContext:
        """Start a new session.

        Args:
            session_id: Unique session identifier
            conversation_mode: True for multi-turn, False for single command

        Returns:
            New SessionContext
        """
        self._session = SessionContext(
            session_id=session_id,
            room_id=self._room_id,
            conversation_mode=conversation_mode
        )
        logger.info(
            f"Session started: {session_id} "
            f"(room={self._room_id}, mode={'multi-turn' if conversation_mode else 'single'})"
        )
        return self._session

    def end_session(self) -> Optional[SessionContext]:
        """End current session.

        Returns:
            The ended session context, or None if no session
        """
        session = self._session
        if session:
            duration = time.time() - session.created_at
            logger.info(
                f"Session ended: {session.session_id} "
                f"(duration={duration:.1f}s, turns={session.turn_count})"
            )
        self._session = None
        return session

    def reset(self) -> None:
        """Reset to idle state, ending any active session."""
        if self._session:
            self.end_session()
        self._state = VoiceState.IDLE
        self._state_entered_at = time.time()
        logger.info("State machine reset to IDLE")

    def is_active(self) -> bool:
        """Check if currently in an active session (not IDLE)."""
        return self._state != VoiceState.IDLE

    def is_listening(self) -> bool:
        """Check if currently listening for speech."""
        return self._state in {VoiceState.LISTENING, VoiceState.WAITING}

    def is_busy(self) -> bool:
        """Check if currently processing (can't accept new input)."""
        return self._state in {VoiceState.TRANSCRIBING, VoiceState.PROCESSING, VoiceState.SPEAKING}

    def get_status_string(self) -> str:
        """Get human-readable status string for MQTT/UI.

        Returns:
            Status string matching AssistantStatus type
        """
        status_map = {
            VoiceState.IDLE: "idle",
            VoiceState.WAKE_DETECTED: "wake_detected",  # Match dashboard VoiceState
            VoiceState.LISTENING: "listening",
            VoiceState.TRANSCRIBING: "transcribing",  # Match dashboard VoiceState
            VoiceState.PROCESSING: "processing",
            VoiceState.SPEAKING: "speaking",
            VoiceState.WAITING: "waiting",  # Match dashboard VoiceState
        }
        return status_map.get(self._state, "idle")


class InteractionResult:
    """Result from processing a single interaction.

    Captures all outputs from one interaction cycle for logging,
    MQTT publishing, and decision making.
    """

    def __init__(self):
        self.transcript: str = ""
        self.response: str = ""
        self.stt_engine: str = ""
        self.stt_duration: float = 0.0
        self.llm_duration: float = 0.0
        self.tts_duration: float = 0.0
        self.is_end_command: bool = False
        self.error: Optional[str] = None
        self.should_continue: bool = True

    @property
    def total_duration(self) -> float:
        """Total processing time."""
        return self.stt_duration + self.llm_duration + self.tts_duration

    def __repr__(self) -> str:
        return (
            f"InteractionResult(transcript='{self.transcript[:30]}...', "
            f"response='{self.response[:30]}...', "
            f"continue={self.should_continue})"
        )
