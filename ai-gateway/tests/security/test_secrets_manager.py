"""Tests for SecretsManager (Phase 1)."""

import os
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.security.secrets_manager import SecretsManager, get_secrets_manager


class TestSecretsManager:
    """Test SecretsManager functionality."""

    def test_get_secret_from_file(self, tmp_path):
        """Test loading secret from Docker Secrets file."""
        # Create mock secret file
        secret_file = tmp_path / "test_token"
        secret_file.write_text("my_secret_value")

        # Initialize secrets manager with temp directory
        manager = SecretsManager(secrets_path=tmp_path)

        # Get secret
        value = manager.get_secret("test_token", required=True)

        assert value == "my_secret_value"

    def test_get_secret_from_env_fallback(self, tmp_path):
        """Test fallback to environment variable when file doesn't exist."""
        # Set environment variable
        os.environ["TEST_SECRET"] = "env_value"

        try:
            # Initialize secrets manager with non-existent path
            manager = SecretsManager(secrets_path=tmp_path)

            # Get secret (should fallback to env)
            value = manager.get_secret("test_secret", required=False)

            assert value == "env_value"
        finally:
            # Cleanup
            del os.environ["TEST_SECRET"]

    def test_get_secret_required_missing(self, tmp_path):
        """Test error when required secret is missing."""
        manager = SecretsManager(secrets_path=tmp_path)

        with pytest.raises(ValueError, match="Secret 'missing_secret' not found"):
            manager.get_secret("missing_secret", required=True)

    def test_get_secret_optional_missing(self, tmp_path):
        """Test None returned when optional secret is missing."""
        manager = SecretsManager(secrets_path=tmp_path)

        value = manager.get_secret("missing_secret", required=False)

        assert value is None

    def test_secret_caching(self, tmp_path):
        """Test that secrets are cached after first read."""
        # Create secret file
        secret_file = tmp_path / "cached_token"
        secret_file.write_text("original_value")

        manager = SecretsManager(secrets_path=tmp_path)

        # First read
        value1 = manager.get_secret("cached_token")
        assert value1 == "original_value"

        # Change file content
        secret_file.write_text("updated_value")

        # Second read (should return cached value)
        value2 = manager.get_secret("cached_token")
        assert value2 == "original_value"

        # Clear cache
        manager.clear_cache()

        # Third read (should read new value)
        value3 = manager.get_secret("cached_token")
        assert value3 == "updated_value"

    def test_validate_all_secrets(self, tmp_path):
        """Test validation of all required secrets."""
        # Create required secrets
        (tmp_path / "ha_token").write_text("ha_test_token")
        (tmp_path / "postgres_password").write_text("pg_test_pass")

        # Create optional secret
        (tmp_path / "openai_api_key").write_text("openai_test_key")

        manager = SecretsManager(secrets_path=tmp_path)

        results = manager.validate_all_secrets()

        assert results["ha_token"] is True
        assert results["postgres_password"] is True
        assert results["openai_api_key"] is True
        assert results["brave_api_key"] is False  # Not created

    def test_validate_all_secrets_missing_required(self, tmp_path):
        """Test validation fails when required secrets are missing."""
        # Only create one required secret
        (tmp_path / "ha_token").write_text("ha_test_token")

        manager = SecretsManager(secrets_path=tmp_path)

        results = manager.validate_all_secrets()

        assert results["ha_token"] is True
        assert results["postgres_password"] is False  # Missing

    def test_secret_whitespace_stripped(self, tmp_path):
        """Test that secrets with whitespace are stripped."""
        secret_file = tmp_path / "whitespace_token"
        secret_file.write_text("  token_with_spaces  \n")

        manager = SecretsManager(secrets_path=tmp_path)

        value = manager.get_secret("whitespace_token")

        assert value == "token_with_spaces"

    def test_get_secrets_manager_singleton(self):
        """Test that get_secrets_manager returns singleton instance."""
        # Get instance twice
        manager1 = get_secrets_manager()
        manager2 = get_secrets_manager()

        # Should be same instance
        assert manager1 is manager2


# Integration test (skipped if /run/secrets doesn't exist)
@pytest.mark.skipif(not Path("/run/secrets").exists(), reason="Docker Secrets not available")
def test_docker_secrets_integration():
    """Test integration with real Docker Secrets (if available)."""
    manager = SecretsManager()

    # Try to load ha_token (may or may not exist)
    try:
        token = manager.get_secret("ha_token", required=False)
        if token:
            assert isinstance(token, str)
            assert len(token) > 10  # JWT tokens are long
    except Exception as e:
        pytest.fail(f"Docker Secrets integration failed: {e}")
