"""Tests for IntentAnalyzer."""

import pytest
from app.services.learning.intent_analyzer import IntentAnalyzer


@pytest.fixture
def analyzer():
    """Fixture providing IntentAnalyzer instance."""
    return IntentAnalyzer()


class TestIntentAnalyzer:
    """Test suite for IntentAnalyzer."""

    # Question detection tests
    def test_should_keep_overlay_open_for_question_mark(self, analyzer):
        """Test overlay stays open for questions ending with question mark."""
        assert analyzer.should_keep_overlay_open("What is the weather?") is True
        assert analyzer.should_keep_overlay_open("Jaka jest pogoda?") is True

    def test_should_keep_overlay_open_for_english_question_words(self, analyzer):
        """Test overlay stays open for English question words."""
        assert analyzer.should_keep_overlay_open("What time is it?") is True
        assert analyzer.should_keep_overlay_open("How are you?") is True
        assert analyzer.should_keep_overlay_open("Where is the living room?") is True
        assert analyzer.should_keep_overlay_open("When will it rain?") is True
        assert analyzer.should_keep_overlay_open("Why did this happen?") is True
        assert analyzer.should_keep_overlay_open("Who is calling?") is True

    def test_should_keep_overlay_open_for_polish_question_words(self, analyzer):
        """Test overlay stays open for Polish question words."""
        assert analyzer.should_keep_overlay_open("Co to jest?") is True
        assert analyzer.should_keep_overlay_open("Który pokój?") is True
        assert analyzer.should_keep_overlay_open("Jak to działa?") is True
        assert analyzer.should_keep_overlay_open("Kiedy to się stanie?") is True
        assert analyzer.should_keep_overlay_open("Gdzie jest kuchnia?") is True
        assert analyzer.should_keep_overlay_open("Dlaczego to nie działa?") is True
        assert analyzer.should_keep_overlay_open("Kto dzwoni?") is True

    def test_should_keep_overlay_open_for_confirmations_requests(self, analyzer):
        """Test overlay stays open for confirmation requests."""
        assert analyzer.should_keep_overlay_open("Would you like me to turn on the lights?") is True
        assert analyzer.should_keep_overlay_open("Do you want the temperature higher?") is True
        assert analyzer.should_keep_overlay_open("Should I dim the lights?") is True
        assert analyzer.should_keep_overlay_open("Czy chcesz włączyć światło?") is True
        assert analyzer.should_keep_overlay_open("Czy mam to zrobić?") is True

    # Confirmation detection tests
    def test_should_close_overlay_for_confirmations(self, analyzer):
        """Test overlay closes for completion confirmations."""
        assert analyzer.should_keep_overlay_open("OK") is False
        assert analyzer.should_keep_overlay_open("Done") is False
        assert analyzer.should_keep_overlay_open("Completed") is False
        assert analyzer.should_keep_overlay_open("Finished") is False
        assert analyzer.should_keep_overlay_open("Gotowe") is False
        assert analyzer.should_keep_overlay_open("Zrobione") is False

    def test_should_close_overlay_for_action_confirmations(self, analyzer):
        """Test overlay closes for action completion statements."""
        assert analyzer.should_keep_overlay_open("Turned on the lights") is False
        assert analyzer.should_keep_overlay_open("Lights turned off") is False
        assert analyzer.should_keep_overlay_open("Światło włączone") is False
        assert analyzer.should_keep_overlay_open("Wyłączyłem ogrzewanie") is False

    def test_should_close_overlay_for_positive_confirmations(self, analyzer):
        """Test overlay closes for positive acknowledgments."""
        assert analyzer.should_keep_overlay_open("Świetnie") is False
        assert analyzer.should_keep_overlay_open("Dobrze") is False
        assert analyzer.should_keep_overlay_open("Super") is False
        assert analyzer.should_keep_overlay_open("Okej") is False

    # Error detection tests
    def test_should_keep_overlay_open_for_errors(self, analyzer):
        """Test overlay stays open for error messages."""
        assert analyzer.should_keep_overlay_open("Error: Connection failed") is True
        assert analyzer.should_keep_overlay_open("Failed to turn on lights") is True
        assert analyzer.should_keep_overlay_open("Nie udało się włączyć światła") is True
        assert analyzer.should_keep_overlay_open("Błąd połączenia") is True
        assert analyzer.should_keep_overlay_open("Problem with the device") is True

    def test_should_keep_overlay_open_for_apologies(self, analyzer):
        """Test overlay stays open for apology messages."""
        assert analyzer.should_keep_overlay_open("Sorry, I couldn't do that") is True
        assert analyzer.should_keep_overlay_open("Przepraszam, nie mogłem tego zrobić") is True
        assert analyzer.should_keep_overlay_open("Unfortunately, that failed") is True
        assert analyzer.should_keep_overlay_open("Przykro mi, nie mogę") is True

    # Edge cases
    def test_should_close_overlay_for_empty_response(self, analyzer):
        """Test overlay closes for empty responses."""
        assert analyzer.should_keep_overlay_open("") is False
        assert analyzer.should_keep_overlay_open("   ") is False

    def test_should_keep_overlay_open_by_default(self, analyzer):
        """Test overlay stays open for unclear responses by default."""
        assert analyzer.should_keep_overlay_open("Some random text") is True
        assert analyzer.should_keep_overlay_open("This is a normal statement") is True

    # Intent type classification
    def test_get_intent_type_question(self, analyzer):
        """Test intent classification for questions."""
        assert analyzer.get_intent_type("What time is it?") == "question"
        assert analyzer.get_intent_type("Jaka jest pogoda?") == "question"

    def test_get_intent_type_confirmation(self, analyzer):
        """Test intent classification for confirmations."""
        assert analyzer.get_intent_type("Done") == "confirmation"
        assert analyzer.get_intent_type("Lights turned on") == "confirmation"
        assert analyzer.get_intent_type("Gotowe") == "confirmation"

    def test_get_intent_type_error(self, analyzer):
        """Test intent classification for errors."""
        assert analyzer.get_intent_type("Error occurred") == "error"
        assert analyzer.get_intent_type("Failed to connect") == "error"
        assert analyzer.get_intent_type("Błąd") == "error"

    def test_get_intent_type_unknown(self, analyzer):
        """Test intent classification for unknown responses."""
        assert analyzer.get_intent_type("Random text") == "unknown"
        assert analyzer.get_intent_type("Some statement") == "unknown"

    # Case insensitivity tests
    def test_case_insensitive_matching(self, analyzer):
        """Test pattern matching is case insensitive."""
        assert analyzer.should_keep_overlay_open("WHAT TIME IS IT?") is True
        assert analyzer.should_keep_overlay_open("done") is False
        assert analyzer.should_keep_overlay_open("ERROR") is True

    # Mixed content tests
    def test_question_in_middle_of_text(self, analyzer):
        """Test question detection in longer text."""
        assert analyzer.should_keep_overlay_open("I turned on the lights. What next?") is True

    def test_error_takes_precedence(self, analyzer):
        """Test error patterns take precedence in classification."""
        # Error should be detected even if question word present
        assert analyzer.get_intent_type("What error occurred?") == "error"
