"""URL validation with domain allowlisting."""

from urllib.parse import urlparse, ParseResult
from typing import Optional
import re
import logging

logger = logging.getLogger(__name__)


class URLValidator:
    """Validate URLs against an allowlist of domains."""

    # Default allowed domains
    DEFAULT_ALLOWED_DOMAINS = [
        # Video
        "youtube.com",
        "youtu.be",
        "vimeo.com",

        # Weather
        "openweathermap.org",
        "weather.com",

        # Maps
        "google.com/maps",
        "openstreetmap.org",

        # News
        "news.google.com",

        # Home Assistant
        "home-assistant.io",
    ]

    # Blocked schemes
    BLOCKED_SCHEMES = [
        "javascript",
        "data",
        "file",
        "ftp",
    ]

    def __init__(self, allowed_domains: Optional[list[str]] = None):
        """
        Initialize URL validator.

        Args:
            allowed_domains: List of allowed domain patterns.
                           If None, uses DEFAULT_ALLOWED_DOMAINS.
        """
        self.allowed_domains = allowed_domains or self.DEFAULT_ALLOWED_DOMAINS
        logger.info(f"URL validator initialized with {len(self.allowed_domains)} allowed domains")

    def validate(self, url: str) -> tuple[bool, str, Optional[str]]:
        """
        Validate URL against security rules.

        Args:
            url: URL string to validate

        Returns:
            Tuple of (is_valid, normalized_url, error_message)
            - is_valid: True if URL passes validation
            - normalized_url: Normalized URL (with https:// prefix if missing)
            - error_message: Error description if invalid, None if valid
        """
        # Check empty
        if not url or not url.strip():
            return False, "", "URL cannot be empty"

        url = url.strip()

        # Add https:// if no scheme
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        # Parse URL
        try:
            parsed: ParseResult = urlparse(url)
        except Exception as e:
            return False, url, f"Invalid URL format: {e}"

        # Check scheme
        if parsed.scheme.lower() in self.BLOCKED_SCHEMES:
            return False, url, f"Blocked URL scheme: {parsed.scheme}"

        if parsed.scheme.lower() not in ("http", "https"):
            return False, url, f"Only HTTP/HTTPS schemes allowed, got: {parsed.scheme}"

        # Check domain allowlist
        domain = parsed.netloc.lower()
        if not domain:
            return False, url, "URL missing domain"

        # Remove port from domain for checking
        domain_without_port = domain.split(":")[0]

        # Check if domain matches any allowed pattern
        allowed = False
        for allowed_domain in self.allowed_domains:
            # Exact match
            if domain_without_port == allowed_domain.lower():
                allowed = True
                break

            # Subdomain match (e.g., "youtube.com" allows "www.youtube.com")
            if domain_without_port.endswith(f".{allowed_domain.lower()}"):
                allowed = True
                break

            # Path-based match (e.g., "google.com/maps")
            if "/" in allowed_domain:
                pattern_domain, pattern_path = allowed_domain.split("/", 1)
                if domain_without_port == pattern_domain.lower():
                    if parsed.path.lstrip("/").startswith(pattern_path):
                        allowed = True
                        break

        if not allowed:
            return False, url, f"Domain not in allowlist: {domain}"

        # Check for path traversal
        if ".." in parsed.path:
            return False, url, "Path traversal detected"

        # All checks passed
        return True, url, None

    def add_domain(self, domain: str):
        """Add a domain to the allowlist."""
        if domain not in self.allowed_domains:
            self.allowed_domains.append(domain)
            logger.info(f"Added domain to allowlist: {domain}")

    def remove_domain(self, domain: str):
        """Remove a domain from the allowlist."""
        if domain in self.allowed_domains:
            self.allowed_domains.remove(domain)
            logger.info(f"Removed domain from allowlist: {domain}")


# Singleton instance
_url_validator: Optional[URLValidator] = None


def get_url_validator() -> URLValidator:
    """Get global URLValidator instance."""
    global _url_validator
    if _url_validator is None:
        # Load custom domains from config if available
        import os
        custom_domains = os.getenv("ALLOWED_DOMAINS", "")
        domains = [d.strip() for d in custom_domains.split(",") if d.strip()]

        if domains:
            _url_validator = URLValidator(allowed_domains=domains)
        else:
            _url_validator = URLValidator()

    return _url_validator
