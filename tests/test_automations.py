"""Tests for Home Assistant automations validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.asyncio

CONFIG_DIR = Path(__file__).parent.parent / "config"
AUTOMATIONS_FILE = CONFIG_DIR / "automations.yaml"


class TestAutomationsStructure:
    """Test suite for validating automation file structure."""

    def test_automations_file_exists(self) -> None:
        """Test that automations.yaml exists."""
        assert AUTOMATIONS_FILE.exists(), "automations.yaml should exist"

    def test_automations_file_valid_yaml(self) -> None:
        """Test that automations.yaml has valid YAML syntax."""
        try:
            with open(AUTOMATIONS_FILE, encoding="utf-8") as f:
                content = yaml.safe_load(f)

            # Should be None (empty) or a list of automations
            assert content is None or isinstance(
                content, list
            ), "automations.yaml should contain a list or be empty"

        except yaml.YAMLError as err:
            pytest.fail(f"automations.yaml has invalid YAML syntax: {err}")

    def test_automations_have_required_fields(self) -> None:
        """Test that each automation has required fields."""
        with open(AUTOMATIONS_FILE, encoding="utf-8") as f:
            automations = yaml.safe_load(f)

        if automations is None:
            pytest.skip("No automations defined")

        assert isinstance(automations, list), "Automations should be a list"

        required_fields = ["trigger", "action"]

        for idx, automation in enumerate(automations):
            assert isinstance(automation, dict), f"Automation {idx} should be a dict"

            # Each automation should have at least trigger and action
            for field in required_fields:
                assert field in automation, (
                    f"Automation {idx} missing required field: {field}"
                )


class TestAutomationSchema:
    """Test suite for validating automation schema compliance."""

    @pytest.fixture
    def automations(self) -> list[dict[str, Any]]:
        """Load automations from file."""
        with open(AUTOMATIONS_FILE, encoding="utf-8") as f:
            content = yaml.safe_load(f)

        if content is None:
            pytest.skip("No automations defined")

        return content

    def test_automation_ids_unique(self, automations: list[dict[str, Any]]) -> None:
        """Test that automation IDs are unique."""
        ids = [auto.get("id") for auto in automations if auto.get("id")]

        if not ids:
            pytest.skip("No automation IDs defined")

        assert len(ids) == len(set(ids)), "Automation IDs should be unique"

    def test_automation_aliases_exist(self, automations: list[dict[str, Any]]) -> None:
        """Test that automations have human-readable aliases."""
        for idx, automation in enumerate(automations):
            assert "alias" in automation or "id" in automation, (
                f"Automation {idx} should have either 'alias' or 'id'"
            )

    def test_triggers_valid_format(self, automations: list[dict[str, Any]]) -> None:
        """Test that triggers are in valid format."""
        for idx, automation in enumerate(automations):
            trigger = automation.get("trigger")

            if trigger is None:
                continue

            # Trigger should be a dict or list of dicts
            if isinstance(trigger, dict):
                trigger = [trigger]

            assert isinstance(trigger, list), (
                f"Automation {idx} trigger should be dict or list"
            )

            for trigger_idx, trig in enumerate(trigger):
                assert isinstance(trig, dict), (
                    f"Automation {idx} trigger {trigger_idx} should be a dict"
                )
                assert "platform" in trig, (
                    f"Automation {idx} trigger {trigger_idx} missing 'platform'"
                )

    def test_actions_valid_format(self, automations: list[dict[str, Any]]) -> None:
        """Test that actions are in valid format."""
        for idx, automation in enumerate(automations):
            action = automation.get("action")

            if action is None:
                continue

            # Action should be a dict or list of dicts
            if isinstance(action, dict):
                action = [action]

            assert isinstance(action, list), (
                f"Automation {idx} action should be dict or list"
            )

            for action_idx, act in enumerate(action):
                assert isinstance(act, dict), (
                    f"Automation {idx} action {action_idx} should be a dict"
                )

                # Action should have at least one action key
                action_keys = {
                    "service",
                    "scene",
                    "event",
                    "delay",
                    "wait_template",
                    "condition",
                    "choose",
                    "repeat",
                }
                has_action_key = any(key in act for key in action_keys)
                assert has_action_key, (
                    f"Automation {idx} action {action_idx} should have an action key"
                )

    def test_conditions_valid_format(self, automations: list[dict[str, Any]]) -> None:
        """Test that conditions (if present) are in valid format."""
        for idx, automation in enumerate(automations):
            condition = automation.get("condition")

            if condition is None:
                continue

            # Condition should be a dict or list of dicts
            if isinstance(condition, dict):
                condition = [condition]

            assert isinstance(condition, list), (
                f"Automation {idx} condition should be dict or list"
            )

            for cond_idx, cond in enumerate(condition):
                assert isinstance(cond, dict), (
                    f"Automation {idx} condition {cond_idx} should be a dict"
                )
                assert "condition" in cond, (
                    f"Automation {idx} condition {cond_idx} missing 'condition' key"
                )


class TestAutomationBestPractices:
    """Test suite for automation best practices."""

    @pytest.fixture
    def automations(self) -> list[dict[str, Any]]:
        """Load automations from file."""
        with open(AUTOMATIONS_FILE, encoding="utf-8") as f:
            content = yaml.safe_load(f)

        if content is None:
            pytest.skip("No automations defined")

        return content

    def test_automations_have_descriptions(
        self, automations: list[dict[str, Any]]
    ) -> None:
        """Test that automations have descriptions (best practice)."""
        missing_descriptions = []

        for idx, automation in enumerate(automations):
            if "description" not in automation:
                alias = automation.get("alias", f"automation_{idx}")
                missing_descriptions.append(alias)

        # This is a warning, not a failure
        if missing_descriptions:
            print(
                f"\nWarning: {len(missing_descriptions)} automation(s) "
                f"without descriptions: {', '.join(missing_descriptions[:5])}"
            )

    def test_no_duplicate_aliases(self, automations: list[dict[str, Any]]) -> None:
        """Test that automation aliases are unique."""
        aliases = [auto.get("alias") for auto in automations if auto.get("alias")]

        if not aliases:
            pytest.skip("No automation aliases defined")

        duplicates = [alias for alias in aliases if aliases.count(alias) > 1]
        unique_duplicates = list(set(duplicates))

        assert not unique_duplicates, (
            f"Duplicate automation aliases found: {', '.join(unique_duplicates)}"
        )

    def test_service_calls_use_new_format(
        self, automations: list[dict[str, Any]]
    ) -> None:
        """Test that service calls use new format (domain.service)."""
        for idx, automation in enumerate(automations):
            actions = automation.get("action", [])

            if isinstance(actions, dict):
                actions = [actions]

            for action_idx, action in enumerate(actions):
                service = action.get("service")

                if service and isinstance(service, str):
                    # Service should be in format "domain.service"
                    assert "." in service or service in ["homeassistant"], (
                        f"Automation {idx} action {action_idx} service '{service}' "
                        f"should use domain.service format"
                    )


class TestAutomationSecurity:
    """Test suite for automation security best practices."""

    @pytest.fixture
    def automations(self) -> list[dict[str, Any]]:
        """Load automations from file."""
        with open(AUTOMATIONS_FILE, encoding="utf-8") as f:
            content = yaml.safe_load(f)

        if content is None:
            pytest.skip("No automations defined")

        return content

    def test_no_hardcoded_secrets(self, automations: list[dict[str, Any]]) -> None:
        """Test that automations don't contain hardcoded secrets."""
        import re

        # Read raw file content
        with open(AUTOMATIONS_FILE, encoding="utf-8") as f:
            content = f.read()

        # Patterns that might indicate hardcoded secrets
        suspicious_patterns = [
            r"password:\s*['\"][^'\"]{8,}['\"]",  # password: "actualpassword"
            r"api_key:\s*['\"][^'\"]{16,}['\"]",  # api_key: "actual_key"
            r"token:\s*['\"][^'\"]{16,}['\"]",  # token: "actual_token"
        ]

        for pattern in suspicious_patterns:
            matches = re.findall(pattern, content)
            if matches:
                # Check if these are comments
                for match in matches:
                    # Find the line
                    lines = content.split("\n")
                    for line in lines:
                        if match in line and not line.strip().startswith("#"):
                            pytest.fail(
                                f"Potential hardcoded secret found: {match}\n"
                                f"Use !secret instead"
                            )

    def test_webhook_ids_not_exposed(self, automations: list[dict[str, Any]]) -> None:
        """Test that webhook IDs are not hardcoded."""
        with open(AUTOMATIONS_FILE, encoding="utf-8") as f:
            content = f.read()

        # Check for long random strings that might be webhook IDs
        import re

        webhook_pattern = r"webhook_id:\s*['\"]?[a-f0-9]{32,}['\"]?"
        matches = re.findall(webhook_pattern, content, re.IGNORECASE)

        if matches:
            print(
                f"\nWarning: Found potential webhook IDs in automations. "
                f"Consider using secrets for webhook IDs."
            )
