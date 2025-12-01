"""
MQTT client for publishing display actions to React Dashboard.

Phase 5: MQTT Decoupling
- Centralized topic configuration
- Versioning support (v1/ prefix)
- Dual v0/v1 publishing during migration

Phase 12: VoiceOverlay UI Redesign
Topic: {version}/voice_assistant/room/{room_id}/session/{session_id}/display_action
Payload: { type: "default" | "web_view" | "light_control" | "search_results", data: {...}, timestamp: int }
"""

import json
import os
import time
import logging
from typing import Any, Dict, Optional
import paho.mqtt.client as mqtt
from app.config.mqtt_topics import get_mqtt_config

logger = logging.getLogger(__name__)


class MqttClient:
    """MQTT client wrapper for publishing display actions."""

    def __init__(self, broker_url: str = "localhost", port: int = 1883):
        """
        Initialize MQTT client.

        Args:
            broker_url: MQTT broker hostname/IP
            port: MQTT broker port (default 1883)
        """
        self.broker_url = broker_url
        self.port = port
        self.client: Optional[mqtt.Client] = None
        self._connected = False
        self.topics = get_mqtt_config()  # Phase 5: Centralized topic config

    def connect(self) -> None:
        """Connect to MQTT broker."""
        if self.client is not None and self._connected:
            return  # Already connected

        try:
            self.client = mqtt.Client()
            self.client.on_connect = self._on_connect
            self.client.on_disconnect = self._on_disconnect

            logger.info(f"Connecting to MQTT broker at {self.broker_url}:{self.port}")
            self.client.connect(self.broker_url, self.port, keepalive=60)
            self.client.loop_start()  # Start network loop in background thread

        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            self.client = None
            self._connected = False

    def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        if self.client is not None:
            self.client.loop_stop()
            self.client.disconnect()
            self.client = None
            self._connected = False
            logger.info("Disconnected from MQTT broker")

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker."""
        if rc == 0:
            self._connected = True
            logger.info("Successfully connected to MQTT broker")
        else:
            self._connected = False
            logger.error(f"Failed to connect to MQTT broker, return code: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker."""
        self._connected = False
        logger.warning(f"Disconnected from MQTT broker, return code: {rc}")

    def publish_display_action(
        self,
        action_type: str,
        action_data: Dict[str, Any],
        room_id: str,
        session_id: str
    ) -> bool:
        """
        Publish a display action to MQTT for the React Dashboard to consume.

        Args:
            action_type: Type of action ("default", "web_view", "light_control", "search_results")
            action_data: Action-specific data payload
            room_id: Room identifier (e.g., "salon", "bedroom")
            session_id: Current session ID

        Returns:
            True if published successfully, False otherwise
        """
        if not self._connected or self.client is None:
            logger.warning("Cannot publish display action: not connected to MQTT broker")
            return False

        try:
            # Phase 5: Use centralized topic config
            topic = self.topics.display_action(room_id, session_id)
            payload = {
                "type": action_type,
                "data": action_data,
                "timestamp": int(time.time() * 1000)  # Milliseconds
            }

            payload_json = json.dumps(payload)

            # Publish to v1 topic
            result = self.client.publish(topic, payload_json, qos=1)

            # Phase 5: Dual publishing - also publish to legacy v0 topic during migration
            legacy_topic = self.topics.legacy_display_action(room_id, session_id)
            self.client.publish(legacy_topic, payload_json, qos=1)
            logger.debug(f"Dual-published to v1 ({topic}) and v0 ({legacy_topic})")

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Published display action '{action_type}' to {topic}")
                logger.debug(f"Payload: {payload_json}")
                return True
            else:
                logger.error(f"Failed to publish display action: {result.rc}")
                return False

        except Exception as e:
            logger.error(f"Error publishing display action: {e}")
            return False

    def publish_overlay_hint(
        self,
        keep_open: bool,
        room_id: str,
        session_id: str
    ) -> bool:
        """
        Publish overlay behavior hint from IntentAnalyzer (Phase 3).

        Args:
            keep_open: Whether overlay should stay open (True) or can close (False)
            room_id: Room identifier
            session_id: Current session ID

        Returns:
            True if published successfully, False otherwise
        """
        if not self._connected or self.client is None:
            logger.warning("Cannot publish overlay hint: not connected to MQTT broker")
            return False

        try:
            # Phase 5: Use centralized topic config
            topic = self.topics.overlay_hint(room_id, session_id)
            payload = {
                "keep_open": keep_open,
                "timestamp": int(time.time() * 1000)  # Milliseconds
            }

            payload_json = json.dumps(payload)
            result = self.client.publish(topic, payload_json, qos=1)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Published overlay hint (keep_open={keep_open}) to {topic}")
                return True
            else:
                logger.error(f"Failed to publish overlay hint: {result.rc}")
                return False

        except Exception as e:
            logger.error(f"Error publishing overlay hint: {e}")
            return False


# Global MQTT client instance (singleton pattern)
_mqtt_client: Optional[MqttClient] = None


def get_mqtt_client() -> MqttClient:
    """
    Get or create the global MQTT client instance.

    Returns:
        MqttClient instance
    """
    global _mqtt_client

    if _mqtt_client is None:
        # Read broker URL from environment (defaults to "mosquitto" for Docker)
        broker_url = os.getenv("MQTT_BROKER_URL", "mosquitto")
        port = int(os.getenv("MQTT_BROKER_PORT", "1883"))
        _mqtt_client = MqttClient(broker_url=broker_url, port=port)
        _mqtt_client.connect()

    return _mqtt_client


def ensure_mqtt_connected() -> None:
    """Ensure MQTT client is connected, reconnect if necessary."""
    client = get_mqtt_client()
    if not client._connected:
        client.connect()
