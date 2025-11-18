"""Tests for custom integrations setup and behavior."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_CLIENT_ID, CONF_CLIENT_SECRET
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

pytestmark = pytest.mark.asyncio

CONFIG_DIR = Path(__file__).parent.parent / "config"
CUSTOM_COMPONENTS_DIR = CONFIG_DIR / "custom_components"


class TestCustomComponentStructure:
    """Test suite for validating custom component structure."""

    @pytest.fixture
    def component_dirs(self) -> list[Path]:
        """Get list of custom component directories."""
        return [
            d
            for d in CUSTOM_COMPONENTS_DIR.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    def test_components_have_init_file(self, component_dirs: list[Path]) -> None:
        """Test that each component has an __init__.py file."""
        for component_dir in component_dirs:
            init_file = component_dir / "__init__.py"
            assert (
                init_file.exists()
            ), f"{component_dir.name} should have __init__.py"

    def test_manifest_versions_valid(self, component_dirs: list[Path]) -> None:
        """Test that manifest versions follow semantic versioning."""
        import re

        # Allow optional leading 'v' prefix (common in many projects)
        semver_pattern = r"^v?\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$"

        for component_dir in component_dirs:
            manifest_file = component_dir / "manifest.json"
            if not manifest_file.exists():
                continue

            with open(manifest_file, encoding="utf-8") as f:
                manifest = json.load(f)

            version = manifest.get("version", "")
            assert re.match(
                semver_pattern, version
            ), f"{component_dir.name} version '{version}' should follow semver (with optional 'v' prefix)"

    def test_manifest_requirements_format(self, component_dirs: list[Path]) -> None:
        """Test that manifest requirements are properly formatted."""
        for component_dir in component_dirs:
            manifest_file = component_dir / "manifest.json"
            if not manifest_file.exists():
                continue

            with open(manifest_file, encoding="utf-8") as f:
                manifest = json.load(f)

            requirements = manifest.get("requirements", [])
            assert isinstance(
                requirements, list
            ), f"{component_dir.name} requirements should be a list"

            for req in requirements:
                assert isinstance(
                    req, str
                ), f"{component_dir.name} requirement should be string: {req}"
                # Should have package name (may include version spec)
                assert (
                    len(req.split(">=")[0].strip()) > 0
                ), f"{component_dir.name} requirement malformed: {req}"


class TestStravaIntegrations:
    """Test suite for Strava-related integrations."""

    @pytest.fixture
    def strava_coach_manifest(self) -> dict[str, Any]:
        """Load strava_coach manifest."""
        manifest_path = CUSTOM_COMPONENTS_DIR / "strava_coach" / "manifest.json"
        if not manifest_path.exists():
            pytest.skip("strava_coach not installed")

        with open(manifest_path, encoding="utf-8") as f:
            return json.load(f)

    @pytest.fixture
    def ha_strava_manifest(self) -> dict[str, Any]:
        """Load ha_strava manifest."""
        manifest_path = CUSTOM_COMPONENTS_DIR / "ha_strava" / "manifest.json"
        if not manifest_path.exists():
            pytest.skip("ha_strava not installed")

        with open(manifest_path, encoding="utf-8") as f:
            return json.load(f)

    def test_strava_coach_domain(self, strava_coach_manifest: dict[str, Any]) -> None:
        """Test that strava_coach has correct domain."""
        assert strava_coach_manifest["domain"] == "strava_coach"

    def test_ha_strava_domain(self, ha_strava_manifest: dict[str, Any]) -> None:
        """Test that ha_strava has correct domain."""
        assert ha_strava_manifest["domain"] == "ha_strava"

    def test_strava_integrations_different_domains(
        self,
        strava_coach_manifest: dict[str, Any],
        ha_strava_manifest: dict[str, Any],
    ) -> None:
        """Test that both Strava integrations have different domains."""
        assert (
            strava_coach_manifest["domain"] != ha_strava_manifest["domain"]
        ), "Strava integrations should have different domains"

    def test_strava_coach_has_config_flow(
        self, strava_coach_manifest: dict[str, Any]
    ) -> None:
        """Test that strava_coach supports config flow."""
        assert strava_coach_manifest.get(
            "config_flow", False
        ), "strava_coach should support config flow"

    def test_strava_coach_files_exist(self) -> None:
        """Test that strava_coach has expected files."""
        strava_coach_dir = CUSTOM_COMPONENTS_DIR / "strava_coach"
        if not strava_coach_dir.exists():
            pytest.skip("strava_coach not installed")

        expected_files = [
            "__init__.py",
            "manifest.json",
            "sensor.py",  # Should have sensor platform
        ]

        for expected_file in expected_files:
            file_path = strava_coach_dir / expected_file
            assert file_path.exists(), f"strava_coach should have {expected_file}"


class TestIntegrationMocking:
    """Test suite for integration setup with mocked Home Assistant."""

    async def test_mock_integration_setup(
        self,
        mock_hass: HomeAssistant,
        mock_config: ConfigType,
    ) -> None:
        """Test that we can mock integration setup."""
        # This is a basic test to ensure our fixtures work
        assert mock_hass is not None
        assert mock_config is not None
        assert isinstance(mock_config, dict)

    async def test_config_entry_creation(
        self,
        mock_config_entry: ConfigEntry,
    ) -> None:
        """Test that config entry fixture works."""
        assert mock_config_entry is not None
        assert mock_config_entry.domain == "test_integration"
        assert CONF_CLIENT_ID in mock_config_entry.data
        assert CONF_CLIENT_SECRET in mock_config_entry.data

    async def test_aiohttp_session_mock(
        self,
        mock_aiohttp_session: AsyncMock,
    ) -> None:
        """Test that aiohttp session mock works."""
        # Simulate API call
        response = await mock_aiohttp_session.get("https://api.example.com/test")
        assert response.status == 200

        data = await response.json()
        assert data["status"] == "ok"

    async def test_entity_registry_mock(
        self,
        mock_entity_registry: MagicMock,
    ) -> None:
        """Test that entity registry mock works."""
        assert mock_entity_registry is not None
        assert hasattr(mock_entity_registry, "async_get")
        assert hasattr(mock_entity_registry, "async_get_entity_id")


class TestYAMLConfiguration:
    """Test suite for YAML configuration patterns."""

    def test_secrets_referenced_correctly(self) -> None:
        """Test that secrets are referenced using !secret tag."""
        config_file = CONFIG_DIR / "configuration.yaml"

        with open(config_file, encoding="utf-8") as f:
            content = f.read()

        # Check that secrets are used (not hardcoded)
        if "strava" in content.lower():
            assert "!secret strava_client_id" in content, (
                "Should use !secret for strava_client_id"
            )
            assert "!secret strava_client_secret" in content, (
                "Should use !secret for strava_client_secret"
            )

    def test_no_hardcoded_secrets_in_config(self) -> None:
        """Test that no obvious secrets are hardcoded."""
        config_file = CONFIG_DIR / "configuration.yaml"

        with open(config_file, encoding="utf-8") as f:
            content = f.read()

        # Common patterns that might indicate hardcoded secrets
        forbidden_patterns = [
            "api_key: ['\"]",  # api_key: "actual_key"
            "password: ['\"]",  # password: "actual_password"
            "token: ['\"]",  # token: "actual_token"
        ]

        import re

        for pattern in forbidden_patterns:
            matches = re.search(pattern, content)
            if matches:
                # Allow if it's a comment
                line = content[: matches.start()].split("\n")[-1]
                assert line.strip().startswith(
                    "#"
                ), f"Potential hardcoded secret found: {pattern}"


class TestDeploymentScripts:
    """Test suite for deployment script validation."""

    def test_deployment_scripts_executable(self) -> None:
        """Test that deployment scripts are executable."""
        scripts_dir = Path(__file__).parent.parent / "scripts"
        deploy_scripts = [
            "deploy_via_ssh.sh",
            "deploy_via_webhook.sh",
        ]

        for script_name in deploy_scripts:
            script_path = scripts_dir / script_name
            if script_path.exists():
                # Check if file has execute permission
                import stat

                file_stat = script_path.stat()
                is_executable = bool(file_stat.st_mode & stat.S_IXUSR)
                assert (
                    is_executable
                ), f"{script_name} should be executable"

    def test_scripts_have_shebang(self) -> None:
        """Test that shell scripts have proper shebang."""
        scripts_dir = Path(__file__).parent.parent / "scripts"
        shell_scripts = list(scripts_dir.glob("*.sh"))

        for script in shell_scripts:
            with open(script, encoding="utf-8") as f:
                first_line = f.readline().strip()

            assert first_line.startswith(
                "#!/"
            ), f"{script.name} should have shebang"
            assert "bash" in first_line.lower() or "sh" in first_line.lower(), (
                f"{script.name} should use bash or sh"
            )
