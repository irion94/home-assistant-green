"""Mock MQTT client for testing without live broker.

Phase 5: MQTT Decoupling
- Testable MQTT abstraction
- Topic pattern matching with wildcards (+, #)
- Message simulation and verification
"""

import re
from typing import Callable, Dict, List, Any
from collections import defaultdict


class MockMQTTClient:
    """Mock MQTT client that simulates broker behavior without network connection."""

    def __init__(self):
        """Initialize mock client with empty message history."""
        self.published_messages: List[Dict[str, Any]] = []
        self.subscriptions: Dict[str, List[Callable]] = defaultdict(list)
        self.is_connected = False

    def connect(self) -> None:
        """Simulate connection to MQTT broker."""
        self.is_connected = True

    def disconnect(self) -> None:
        """Simulate disconnection from MQTT broker."""
        self.is_connected = False
        self.published_messages.clear()
        self.subscriptions.clear()

    def publish(self, topic: str, payload: str, qos: int = 0) -> None:
        """
        Simulate publishing a message.

        Args:
            topic: MQTT topic string
            payload: Message payload (typically JSON string)
            qos: Quality of Service level (0, 1, 2)
        """
        self.published_messages.append({
            "topic": topic,
            "payload": payload,
            "qos": qos
        })

        # Trigger subscriptions that match this topic
        for pattern, callbacks in self.subscriptions.items():
            if self._topic_matches(topic, pattern):
                for callback in callbacks:
                    callback(topic, payload)

    def subscribe(self, topic: str, callback: Callable) -> None:
        """
        Simulate subscribing to a topic.

        Args:
            topic: MQTT topic pattern (supports + and # wildcards)
            callback: Function called when matching message received
        """
        self.subscriptions[topic].append(callback)

    def simulate_message(self, topic: str, payload: str) -> None:
        """
        Simulate receiving a message from the broker.

        Args:
            topic: MQTT topic string
            payload: Message payload
        """
        for pattern, callbacks in self.subscriptions.items():
            if self._topic_matches(topic, pattern):
                for callback in callbacks:
                    callback(topic, payload)

    def get_published_to(self, topic_pattern: str) -> List[Dict[str, Any]]:
        """
        Get all messages published to topics matching the pattern.

        Args:
            topic_pattern: MQTT topic pattern (supports + and # wildcards)

        Returns:
            List of published messages with topic, payload, qos
        """
        return [
            msg for msg in self.published_messages
            if self._topic_matches(msg["topic"], topic_pattern)
        ]

    def clear_published(self) -> None:
        """Clear all published message history."""
        self.published_messages.clear()

    def _topic_matches(self, topic: str, pattern: str) -> bool:
        """
        Check if topic matches MQTT subscription pattern.

        Supports MQTT wildcards:
        - + matches single level (e.g., "room/+/state" matches "room/salon/state")
        - # matches multiple levels (e.g., "room/#" matches "room/salon/state/listening")

        Args:
            topic: Actual topic string
            pattern: Subscription pattern with wildcards

        Returns:
            True if topic matches pattern
        """
        # Escape special regex characters except + and #
        pattern_regex = pattern.replace('+', '[^/]+').replace('#', '.*')

        # Exact match required (anchor to start and end)
        pattern_regex = '^' + pattern_regex + '$'

        return bool(re.match(pattern_regex, topic))


# Pytest fixture for easy use in tests
def get_mock_mqtt_client() -> MockMQTTClient:
    """
    Create a new mock MQTT client instance.

    Returns:
        Configured MockMQTTClient
    """
    client = MockMQTTClient()
    client.connect()
    return client
