"""Secrets management with Docker Secrets and environment variable fallback."""

from pathlib import Path
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)


class SecretsManager:
    """Manage secrets from Docker Secrets or environment variables."""

    def __init__(self, secrets_path: Path = Path("/run/secrets")):
        self.secrets_path = secrets_path
        self._cache: dict[str, str] = {}

    def get_secret(self, key: str, required: bool = True) -> Optional[str]:
        """
        Get secret from Docker Secrets or environment variable.

        Priority:
        1. Docker Secret (/run/secrets/{key})
        2. Environment variable
        3. Raise error if required

        Args:
            key: Secret key name (e.g., 'ha_token')
            required: If True, raise error when secret not found

        Returns:
            Secret value or None

        Raises:
            ValueError: If required=True and secret not found
        """
        # Check cache first
        if key in self._cache:
            return self._cache[key]

        # Try Docker Secret
        secret_file = self.secrets_path / key
        if secret_file.exists():
            try:
                value = secret_file.read_text().strip()
                self._cache[key] = value
                logger.info(f"Loaded secret '{key}' from Docker Secrets")
                return value
            except Exception as e:
                logger.error(f"Failed to read Docker Secret '{key}': {e}")

        # Try environment variable
        env_key = key.upper()
        value = os.getenv(env_key)
        if value:
            self._cache[key] = value
            logger.warning(f"Loaded secret '{key}' from environment (fallback)")
            return value

        # Not found
        if required:
            raise ValueError(
                f"Secret '{key}' not found in Docker Secrets or environment. "
                f"Create {secret_file} or set {env_key} environment variable."
            )

        return None

    def validate_all_secrets(self) -> dict[str, bool]:
        """
        Validate all required secrets at startup.

        Returns:
            Dict mapping secret names to validation status
        """
        required_secrets = [
            'ha_token',
            'postgres_password',
        ]

        optional_secrets = [
            'openai_api_key',
            'brave_api_key',
        ]

        results = {}

        # Check required
        for secret in required_secrets:
            try:
                value = self.get_secret(secret, required=True)
                results[secret] = bool(value and len(value) > 0)
            except ValueError:
                results[secret] = False

        # Check optional
        for secret in optional_secrets:
            value = self.get_secret(secret, required=False)
            results[secret] = bool(value)

        return results

    def clear_cache(self):
        """Clear the secrets cache (useful for rotation)."""
        self._cache.clear()
        logger.info("Secrets cache cleared")


# Singleton instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get global SecretsManager instance."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager
