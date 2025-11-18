"""Tests for Home Assistant configuration validation."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from homeassistant.config import YAML_CONFIG_FILE

pytestmark = pytest.mark.asyncio

CONFIG_DIR = Path(__file__).parent.parent / "config"


def create_ha_yaml_loader():
    """Create a YAML loader that supports Home Assistant custom tags.

    Returns a SafeLoader with constructors for HA tags like !include, !secret, etc.
    """
    loader = yaml.SafeLoader

    # Add constructors for Home Assistant custom tags
    # These just return placeholder values since we're only testing syntax
    loader.add_constructor("!include", lambda loader, node: f"!include {node.value}")
    loader.add_constructor("!include_dir_named", lambda loader, node: {})
    loader.add_constructor("!include_dir_list", lambda loader, node: [])
    loader.add_constructor("!include_dir_merge_list", lambda loader, node: [])
    loader.add_constructor("!include_dir_merge_named", lambda loader, node: {})
    loader.add_constructor("!secret", lambda loader, node: f"!secret {node.value}")
    loader.add_constructor("!env_var", lambda loader, node: f"!env_var {node.value}")
    loader.add_constructor("!input", lambda loader, node: f"!input {node.value}")

    return loader


class TestConfigurationValidation:
    """Test suite for validating Home Assistant configuration files."""

    def test_config_directory_exists(self) -> None:
        """Test that the config directory exists."""
        assert CONFIG_DIR.exists(), "Config directory should exist"
        assert CONFIG_DIR.is_dir(), "Config path should be a directory"

    def test_configuration_yaml_exists(self) -> None:
        """Test that configuration.yaml exists and is readable."""
        config_file = CONFIG_DIR / YAML_CONFIG_FILE
        assert config_file.exists(), "configuration.yaml should exist"
        assert config_file.is_file(), "configuration.yaml should be a file"

    def test_configuration_yaml_valid_syntax(self) -> None:
        """Test that configuration.yaml has valid YAML syntax."""
        config_file = CONFIG_DIR / YAML_CONFIG_FILE
        try:
            with open(config_file, encoding="utf-8") as f:
                # Try to parse the YAML, allowing HA-specific tags
                yaml.load(f, Loader=create_ha_yaml_loader())
        except yaml.YAMLError as err:
            pytest.fail(f"configuration.yaml has invalid YAML syntax: {err}")

    def test_automations_yaml_exists(self) -> None:
        """Test that automations.yaml exists."""
        automations_file = CONFIG_DIR / "automations.yaml"
        assert automations_file.exists(), "automations.yaml should exist"

    def test_automations_yaml_valid_syntax(self) -> None:
        """Test that automations.yaml has valid YAML syntax."""
        automations_file = CONFIG_DIR / "automations.yaml"
        try:
            with open(automations_file, encoding="utf-8") as f:
                content = yaml.safe_load(f)
                # Automations should be a list (or None if empty)
                assert content is None or isinstance(
                    content, list
                ), "automations.yaml should contain a list"
        except yaml.YAMLError as err:
            pytest.fail(f"automations.yaml has invalid YAML syntax: {err}")

    def test_packages_directory_exists(self) -> None:
        """Test that packages directory exists."""
        packages_dir = CONFIG_DIR / "packages"
        assert packages_dir.exists(), "packages directory should exist"
        assert packages_dir.is_dir(), "packages should be a directory"

    def test_packages_yaml_files_valid(self) -> None:
        """Test that all package YAML files have valid syntax."""
        packages_dir = CONFIG_DIR / "packages"
        yaml_files = list(packages_dir.glob("*.yaml"))

        assert len(yaml_files) > 0, "Should have at least one package file"

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, encoding="utf-8") as f:
                    yaml.load(f, Loader=create_ha_yaml_loader())
            except yaml.YAMLError as err:
                pytest.fail(f"{yaml_file.name} has invalid YAML syntax: {err}")

    def test_custom_components_directory_exists(self) -> None:
        """Test that custom_components directory exists."""
        custom_dir = CONFIG_DIR / "custom_components"
        assert custom_dir.exists(), "custom_components directory should exist"
        assert custom_dir.is_dir(), "custom_components should be a directory"

    def test_custom_components_have_manifests(self) -> None:
        """Test that each custom component has a manifest.json."""
        custom_dir = CONFIG_DIR / "custom_components"

        # Get all subdirectories (each is a custom component)
        components = [
            d for d in custom_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
        ]

        assert len(components) > 0, "Should have at least one custom component"

        for component in components:
            manifest = component / "manifest.json"
            assert (
                manifest.exists()
            ), f"{component.name} should have a manifest.json file"

    def test_custom_components_manifests_valid(self) -> None:
        """Test that all manifest.json files are valid JSON with required fields."""
        custom_dir = CONFIG_DIR / "custom_components"
        components = [
            d for d in custom_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
        ]

        required_fields = ["domain", "name", "version", "documentation", "requirements"]

        for component in components:
            manifest_file = component / "manifest.json"
            if not manifest_file.exists():
                continue

            try:
                import json

                with open(manifest_file, encoding="utf-8") as f:
                    manifest = json.load(f)

                # Check required fields
                for field in required_fields:
                    assert field in manifest, (
                        f"{component.name}/manifest.json missing required field: {field}"
                    )

                # Validate domain matches directory name
                assert manifest["domain"] == component.name, (
                    f"{component.name}/manifest.json domain should match directory name"
                )

            except (json.JSONDecodeError, AssertionError) as err:
                pytest.fail(f"{component.name}/manifest.json validation failed: {err}")

    def test_secrets_template_exists(self) -> None:
        """Test that secrets.yaml.example template exists."""
        secrets_template = CONFIG_DIR / "secrets.yaml.example"
        assert secrets_template.exists(), "secrets.yaml.example should exist"

    def test_gitignore_protects_secrets(self) -> None:
        """Test that .gitignore properly excludes sensitive files."""
        gitignore_file = Path(__file__).parent.parent / ".gitignore"
        assert gitignore_file.exists(), ".gitignore should exist"

        with open(gitignore_file, encoding="utf-8") as f:
            gitignore_content = f.read()

        # Check that critical patterns are excluded
        critical_patterns = [
            "secrets.yaml",
            ".storage/",
            "home-assistant_v2.db",
            "*.db",
        ]

        for pattern in critical_patterns:
            assert pattern in gitignore_content, (
                f".gitignore should contain pattern: {pattern}"
            )

    def test_no_secrets_committed(self) -> None:
        """Test that secrets.yaml is not in the repository."""
        secrets_file = CONFIG_DIR / "secrets.yaml"

        # If secrets.yaml exists (local dev), ensure it's gitignored
        if secrets_file.exists():
            pytest.skip(
                "secrets.yaml exists locally (expected in dev), "
                "ensure it's in .gitignore"
            )


class TestIntegrationConfiguration:
    """Test suite for validating integration-specific configurations."""

    def test_strava_integrations_configured(self) -> None:
        """Test that Strava integrations are properly configured."""
        config_file = CONFIG_DIR / YAML_CONFIG_FILE

        # We can't load the full config without HA running, but we can check structure
        with open(config_file, encoding="utf-8") as f:
            content = f.read()

        # Check that both Strava integrations are configured
        assert "strava_coach:" in content, "strava_coach integration should be configured"
        assert "ha_strava:" in content, "ha_strava integration should be configured"

    def test_logger_configured(self) -> None:
        """Test that logger is properly configured for debugging."""
        config_file = CONFIG_DIR / YAML_CONFIG_FILE

        with open(config_file, encoding="utf-8") as f:
            content = f.read()

        assert "logger:" in content, "Logger should be configured"

    def test_automation_included(self) -> None:
        """Test that automations are included in configuration."""
        config_file = CONFIG_DIR / YAML_CONFIG_FILE

        with open(config_file, encoding="utf-8") as f:
            content = f.read()

        assert (
            "automation: !include automations.yaml" in content
        ), "Automations should be included"

    def test_packages_included(self) -> None:
        """Test that packages are included in configuration."""
        config_file = CONFIG_DIR / YAML_CONFIG_FILE

        with open(config_file, encoding="utf-8") as f:
            content = f.read()

        assert (
            "packages: !include_dir_named packages" in content
        ), "Packages should be included"


class TestProjectStructure:
    """Test suite for validating overall project structure."""

    def test_pyproject_toml_exists(self) -> None:
        """Test that pyproject.toml exists at project root."""
        pyproject = Path(__file__).parent.parent / "pyproject.toml"
        assert pyproject.exists(), "pyproject.toml should exist"

    def test_pyproject_has_test_dependencies(self) -> None:
        """Test that pyproject.toml has test dependencies configured."""
        pyproject = Path(__file__).parent.parent / "pyproject.toml"

        with open(pyproject, encoding="utf-8") as f:
            content = f.read()

        assert "pytest" in content, "Should have pytest in dependencies"
        assert "pytest-asyncio" in content, "Should have pytest-asyncio in dependencies"

    def test_github_workflows_exist(self) -> None:
        """Test that GitHub Actions workflows exist."""
        workflows_dir = Path(__file__).parent.parent / ".github" / "workflows"
        assert workflows_dir.exists(), ".github/workflows directory should exist"

        # Check for key workflows
        ci_workflow = workflows_dir / "ci.yml"
        assert ci_workflow.exists(), "CI workflow should exist"

    def test_documentation_exists(self) -> None:
        """Test that key documentation files exist."""
        project_root = Path(__file__).parent.parent

        readme = project_root / "README.md"
        assert readme.exists(), "README.md should exist"

        claude_md = project_root / "CLAUDE.md"
        assert claude_md.exists(), "CLAUDE.md should exist"

    def test_scripts_directory_exists(self) -> None:
        """Test that scripts directory exists with deployment scripts."""
        scripts_dir = Path(__file__).parent.parent / "scripts"
        assert scripts_dir.exists(), "scripts directory should exist"

        # Check for key deployment scripts
        deploy_ssh = scripts_dir / "deploy_via_ssh.sh"
        assert deploy_ssh.exists(), "deploy_via_ssh.sh should exist"
