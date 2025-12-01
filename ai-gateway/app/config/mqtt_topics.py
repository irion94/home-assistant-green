"""MQTT topic configuration with versioning support.

Phase 5: MQTT Decoupling
- Centralized topic structure
- Versioning support (v1/ prefix)
- Environment variable configuration
"""

from dataclasses import dataclass
import os


@dataclass
class MQTTTopicConfig:
    """Configuration for MQTT topics with versioning support."""

    version: str = "v1"
    base_prefix: str = "voice_assistant"

    def __post_init__(self):
        # Load from environment
        self.version = os.getenv("MQTT_TOPIC_VERSION", self.version)
        self.base_prefix = os.getenv("MQTT_BASE_PREFIX", self.base_prefix)

    def _base(self, room_id: str, session_id: str) -> str:
        """Build base topic path."""
        return f"{self.version}/{self.base_prefix}/room/{room_id}/session/{session_id}"

    # State topics
    def state(self, room_id: str, session_id: str) -> str:
        """Voice assistant state changes."""
        return f"{self._base(room_id, session_id)}/state"

    # Transcript topics
    def transcript(self, room_id: str, session_id: str) -> str:
        """Legacy transcript topic (for backward compatibility)."""
        return f"{self._base(room_id, session_id)}/transcript"

    def transcript_interim(self, room_id: str, session_id: str) -> str:
        """Streaming STT interim results."""
        return f"{self._base(room_id, session_id)}/transcript/interim"

    def transcript_final(self, room_id: str, session_id: str) -> str:
        """Final STT result from Vosk."""
        return f"{self._base(room_id, session_id)}/transcript/final"

    def transcript_refined(self, room_id: str, session_id: str) -> str:
        """Whisper-refined final transcript."""
        return f"{self._base(room_id, session_id)}/transcript/refined"

    # Response topics
    def response(self, room_id: str, session_id: str) -> str:
        """Complete AI response (non-streaming)."""
        return f"{self._base(room_id, session_id)}/response"

    def response_stream_start(self, room_id: str, session_id: str) -> str:
        """Streaming response started event."""
        return f"{self._base(room_id, session_id)}/response/stream/start"

    def response_stream_chunk(self, room_id: str, session_id: str) -> str:
        """Token-by-token streaming chunks."""
        return f"{self._base(room_id, session_id)}/response/stream/chunk"

    def response_stream_complete(self, room_id: str, session_id: str) -> str:
        """Streaming response completed event."""
        return f"{self._base(room_id, session_id)}/response/stream/complete"

    # Display action topic
    def display_action(self, room_id: str, session_id: str) -> str:
        """UI panel switching commands."""
        return f"{self._base(room_id, session_id)}/display_action"

    # Tool execution topic
    def tool_executed(self, room_id: str, session_id: str) -> str:
        """Tool execution events (debugging/history)."""
        return f"{self._base(room_id, session_id)}/tool_executed"

    # Overlay hint topic
    def overlay_hint(self, room_id: str, session_id: str) -> str:
        """Overlay behavior hints (keep open vs auto-close)."""
        return f"{self._base(room_id, session_id)}/overlay_hint"

    # Subscription patterns (wildcards)
    def subscribe_all_sessions(self, room_id: str) -> str:
        """Subscribe to all sessions in a room."""
        return f"{self.version}/{self.base_prefix}/room/{room_id}/session/+/#"

    def subscribe_session(self, room_id: str, session_id: str) -> str:
        """Subscribe to all topics in a specific session."""
        return f"{self._base(room_id, session_id)}/#"

    # Legacy v0 topics (for backward compatibility during migration)
    def legacy_base(self, room_id: str, session_id: str) -> str:
        """Legacy topic format (no version prefix)."""
        return f"{self.base_prefix}/room/{room_id}/session/{session_id}"

    def legacy_display_action(self, room_id: str, session_id: str) -> str:
        """Legacy display_action topic (v0)."""
        return f"{self.legacy_base(room_id, session_id)}/display_action"

    def subscribe_legacy_sessions(self, room_id: str) -> str:
        """Subscribe to legacy v0 topics."""
        return f"{self.base_prefix}/room/{room_id}/session/+/#"


# Singleton instance
_mqtt_config: MQTTTopicConfig | None = None


def get_mqtt_config() -> MQTTTopicConfig:
    """Get global MQTT topic configuration.

    Returns singleton instance, creating it if necessary.
    Thread-safe for initialization.
    """
    global _mqtt_config
    if _mqtt_config is None:
        _mqtt_config = MQTTTopicConfig()
    return _mqtt_config
