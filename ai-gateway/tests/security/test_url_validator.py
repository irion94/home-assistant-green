"""Tests for URLValidator (Phase 1)."""

import pytest

from app.security.url_validator import URLValidator, get_url_validator


class TestURLValidator:
    """Test URLValidator functionality."""

    def test_valid_url_with_https(self):
        """Test valid URL with https:// scheme."""
        validator = URLValidator()

        is_valid, normalized_url, error = validator.validate("https://youtube.com/watch?v=abc")

        assert is_valid is True
        assert normalized_url == "https://youtube.com/watch?v=abc"
        assert error is None

    def test_valid_url_without_scheme(self):
        """Test valid URL without scheme (should add https://)."""
        validator = URLValidator()

        is_valid, normalized_url, error = validator.validate("youtube.com")

        assert is_valid is True
        assert normalized_url == "https://youtube.com"
        assert error is None

    def test_subdomain_match(self):
        """Test subdomain matching (www.youtube.com allowed if youtube.com in list)."""
        validator = URLValidator()

        is_valid, normalized_url, error = validator.validate("https://www.youtube.com")

        assert is_valid is True
        assert normalized_url == "https://www.youtube.com"
        assert error is None

    def test_blocked_domain(self):
        """Test that non-allowlisted domain is blocked."""
        validator = URLValidator()

        is_valid, normalized_url, error = validator.validate("https://malicious.com")

        assert is_valid is False
        assert "not in allowlist" in error

    def test_blocked_javascript_scheme(self):
        """Test that javascript: scheme is blocked."""
        validator = URLValidator()

        is_valid, normalized_url, error = validator.validate("javascript:alert('xss')")

        assert is_valid is False
        assert "Blocked URL scheme" in error

    def test_blocked_data_scheme(self):
        """Test that data: scheme is blocked."""
        validator = URLValidator()

        is_valid, normalized_url, error = validator.validate("data:text/html,<script>alert('xss')</script>")

        assert is_valid is False
        assert "Blocked URL scheme" in error

    def test_blocked_file_scheme(self):
        """Test that file: scheme is blocked."""
        validator = URLValidator()

        is_valid, normalized_url, error = validator.validate("file:///etc/passwd")

        assert is_valid is False
        assert "Blocked URL scheme" in error

    def test_empty_url(self):
        """Test that empty URL is rejected."""
        validator = URLValidator()

        is_valid, normalized_url, error = validator.validate("")

        assert is_valid is False
        assert "cannot be empty" in error

    def test_whitespace_url(self):
        """Test that whitespace-only URL is rejected."""
        validator = URLValidator()

        is_valid, normalized_url, error = validator.validate("   ")

        assert is_valid is False
        assert "cannot be empty" in error

    def test_path_traversal_blocked(self):
        """Test that path traversal is detected and blocked."""
        validator = URLValidator()

        is_valid, normalized_url, error = validator.validate("https://youtube.com/../etc/passwd")

        assert is_valid is False
        assert "Path traversal" in error

    def test_custom_allowed_domains(self):
        """Test validator with custom allowed domains."""
        validator = URLValidator(allowed_domains=["custom-site.com", "another-site.org"])

        # Custom domain should be allowed
        is_valid, _, _ = validator.validate("https://custom-site.com")
        assert is_valid is True

        # Default domain should be blocked
        is_valid, _, error = validator.validate("https://youtube.com")
        assert is_valid is False
        assert "not in allowlist" in error

    def test_add_domain(self):
        """Test dynamically adding a domain to the allowlist."""
        validator = URLValidator()

        # Initially blocked
        is_valid, _, _ = validator.validate("https://new-domain.com")
        assert is_valid is False

        # Add domain
        validator.add_domain("new-domain.com")

        # Now allowed
        is_valid, _, _ = validator.validate("https://new-domain.com")
        assert is_valid is True

    def test_remove_domain(self):
        """Test dynamically removing a domain from the allowlist."""
        validator = URLValidator()

        # Initially allowed
        is_valid, _, _ = validator.validate("https://youtube.com")
        assert is_valid is True

        # Remove domain
        validator.remove_domain("youtube.com")

        # Now blocked
        is_valid, _, _ = validator.validate("https://youtube.com")
        assert is_valid is False

    def test_path_based_allowlist(self):
        """Test path-based domain matching (e.g., google.com/maps)."""
        validator = URLValidator()

        # google.com/maps is in default allowlist
        is_valid, _, _ = validator.validate("https://google.com/maps")
        assert is_valid is True

        # google.com/search should be blocked (not in allowlist)
        is_valid, _, error = validator.validate("https://google.com/search")
        assert is_valid is False
        assert "not in allowlist" in error

    def test_url_with_port(self):
        """Test URL with custom port."""
        validator = URLValidator()

        is_valid, normalized_url, error = validator.validate("https://youtube.com:8080/watch")

        assert is_valid is True
        assert normalized_url == "https://youtube.com:8080/watch"

    def test_http_scheme_allowed(self):
        """Test that http:// scheme is allowed (not just https://)."""
        validator = URLValidator()

        is_valid, _, _ = validator.validate("http://youtube.com")

        assert is_valid is True

    def test_ftp_scheme_blocked(self):
        """Test that ftp:// scheme is blocked."""
        validator = URLValidator()

        is_valid, _, error = validator.validate("ftp://files.example.com")

        assert is_valid is False
        assert "Blocked URL scheme" in error or "Only HTTP/HTTPS" in error

    def test_missing_domain(self):
        """Test URL with missing domain."""
        validator = URLValidator()

        is_valid, _, error = validator.validate("https://")

        assert is_valid is False
        assert "missing domain" in error.lower()

    def test_invalid_url_format(self):
        """Test completely invalid URL format."""
        validator = URLValidator()

        is_valid, _, error = validator.validate("not a url at all!!!")

        # Should fail validation (either missing domain or not in allowlist)
        assert is_valid is False

    def test_get_url_validator_singleton(self):
        """Test that get_url_validator returns singleton instance."""
        validator1 = get_url_validator()
        validator2 = get_url_validator()

        # Should be same instance
        assert validator1 is validator2

    def test_default_allowed_domains_loaded(self):
        """Test that default allowed domains are loaded."""
        validator = URLValidator()

        # Check a few default domains
        assert "youtube.com" in validator.allowed_domains
        assert "weather.com" in validator.allowed_domains
        assert "openstreetmap.org" in validator.allowed_domains
        assert "home-assistant.io" in validator.allowed_domains

    def test_case_insensitive_domain_matching(self):
        """Test that domain matching is case-insensitive."""
        validator = URLValidator()

        # Test uppercase domain
        is_valid, _, _ = validator.validate("https://YOUTUBE.COM")
        assert is_valid is True

        # Test mixed case
        is_valid, _, _ = validator.validate("https://YouTube.Com")
        assert is_valid is True
