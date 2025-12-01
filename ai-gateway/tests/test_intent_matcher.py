"""Tests for IntentMatcher pattern matching logic."""

from __future__ import annotations

import pytest

from app.services.intent_matcher import IntentMatcher, get_intent_matcher


class TestIntentMatcher:
    """Tests for IntentMatcher."""

    @pytest.fixture
    def matcher(self) -> IntentMatcher:
        """Fixture providing IntentMatcher instance."""
        return IntentMatcher(threshold=65)

    # Turn on/off detection tests
    def test_detect_turn_on_polish(self, matcher: IntentMatcher) -> None:
        """Test Polish turn on commands."""
        action = matcher.match("włącz światło w salonie")
        assert action is not None
        assert action.action == "call_service"
        assert action.service == "light.turn_on"

    def test_detect_turn_off_polish(self, matcher: IntentMatcher) -> None:
        """Test Polish turn off commands."""
        action = matcher.match("wyłącz światło w kuchni")
        assert action is not None
        assert action.action == "call_service"
        assert action.service == "light.turn_off"

    def test_detect_turn_on_english(self, matcher: IntentMatcher) -> None:
        """Test English turn on commands."""
        action = matcher.match("turn on the bedroom light")
        assert action is not None
        assert action.action == "call_service"
        assert action.service == "light.turn_on"

    def test_detect_turn_off_english(self, matcher: IntentMatcher) -> None:
        """Test English turn off commands."""
        action = matcher.match("turn off the kitchen light")
        assert action is not None
        assert action.action == "call_service"
        assert action.service == "light.turn_off"

    # Entity extraction tests
    def test_extract_salon_entity(self, matcher: IntentMatcher) -> None:
        """Test extraction of living room entity."""
        action = matcher.match("włącz światło w salonie")
        assert action is not None
        assert action.entity_id == "light.yeelight_color_0x80156a9"

    def test_extract_bedroom_entity(self, matcher: IntentMatcher) -> None:
        """Test extraction of bedroom entity."""
        action = matcher.match("włącz światło w sypialni")
        assert action is not None
        assert action.entity_id == "light.yeelight_color_0x80147dd"

    def test_extract_kitchen_entity(self, matcher: IntentMatcher) -> None:
        """Test extraction of kitchen entity."""
        action = matcher.match("włącz światło w kuchni")
        assert action is not None
        assert action.entity_id == "light.yeelight_color_0x49c27e1"

    def test_extract_all_lights(self, matcher: IntentMatcher) -> None:
        """Test extraction of 'all' entity."""
        action = matcher.match("wyłącz wszystkie światła")
        assert action is not None
        assert action.entity_id == "all"

    # Confidence score tests
    def test_confidence_exact_match(self, matcher: IntentMatcher) -> None:
        """Test high confidence for exact matches."""
        action, confidence = matcher.match_with_confidence("włącz światło w salonie")
        assert action is not None
        assert confidence >= 0.9

    def test_confidence_fuzzy_match(self, matcher: IntentMatcher) -> None:
        """Test lower confidence for fuzzy matches."""
        action, confidence = matcher.match_with_confidence("wlacz swiatlo w salonie")
        assert action is not None
        assert 0.5 <= confidence <= 1.0

    def test_no_match_returns_none(self, matcher: IntentMatcher) -> None:
        """Test that unrecognized text returns None."""
        action, confidence = matcher.match_with_confidence("random text without commands")
        assert action is None
        assert confidence == 0.0

    # Web search detection tests
    def test_web_search_polish(self, matcher: IntentMatcher) -> None:
        """Test Polish web search detection."""
        action = matcher.match("wyszukaj pogodę w Warszawie")
        assert action is not None
        assert action.action == "web_search"
        assert action.data["query"] == "pogodę w Warszawie"

    def test_web_search_english(self, matcher: IntentMatcher) -> None:
        """Test English web search detection."""
        action = matcher.match("search for weather in Warsaw")
        assert action is not None
        assert action.action == "web_search"
        assert action.data["query"] == "weather in Warsaw"

    def test_web_search_what_is(self, matcher: IntentMatcher) -> None:
        """Test 'what is' question pattern for web search."""
        action = matcher.match("what is the capital of France")
        assert action is not None
        assert action.action == "web_search"
        assert "capital of France" in action.data["query"]

    # Conversation mode tests
    def test_conversation_start_polish(self, matcher: IntentMatcher) -> None:
        """Test Polish conversation start detection."""
        action = matcher.match("porozmawiajmy")
        assert action is not None
        assert action.action == "conversation_start"

    def test_conversation_end_polish(self, matcher: IntentMatcher) -> None:
        """Test Polish conversation end detection."""
        action = matcher.match("zakończ rozmowę")
        assert action is not None
        assert action.action == "conversation_end"

    def test_conversation_start_english(self, matcher: IntentMatcher) -> None:
        """Test English conversation start detection."""
        action = matcher.match("let's talk")
        assert action is not None
        assert action.action == "conversation_start"

    # TTS message extraction tests
    def test_tts_message_polish(self, matcher: IntentMatcher) -> None:
        """Test Polish TTS message extraction."""
        action = matcher.match("powiedz: witaj świecie")
        assert action is not None
        assert action.action == "call_service"
        assert action.service == "tts.speak"
        assert action.data["message"] == "witaj świecie"

    def test_tts_message_english(self, matcher: IntentMatcher) -> None:
        """Test English TTS message extraction."""
        action = matcher.match("say: hello world")
        assert action is not None
        assert action.action == "call_service"
        assert action.service == "tts.speak"
        assert action.data["message"] == "hello world"

    # Media stop tests
    def test_media_stop(self, matcher: IntentMatcher) -> None:
        """Test media stop command."""
        action = matcher.match("stop media")
        assert action is not None
        assert action.action == "call_service"
        assert action.service == "media_player.media_stop"

    # Singleton tests
    def test_get_intent_matcher_singleton(self) -> None:
        """Test that get_intent_matcher returns singleton."""
        matcher1 = get_intent_matcher()
        matcher2 = get_intent_matcher()
        assert matcher1 is matcher2

    def test_threshold_initialization(self) -> None:
        """Test custom threshold initialization."""
        matcher = IntentMatcher(threshold=80)
        assert matcher.threshold == 80
