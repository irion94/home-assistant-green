#!/usr/bin/env python3
"""Validate that all !secret references in YAML files have corresponding entries.

This script scans all YAML configuration files for !secret references and checks
that each referenced secret exists in secrets.yaml (or secrets.yaml.example for CI).

Exit codes:
    0: All secrets are defined
    1: Missing secrets found
    2: Script error
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml


class SecretReference:
    """Represents a secret reference found in a YAML file."""

    def __init__(self, file_path: Path, line_number: int, secret_name: str) -> None:
        """Initialize a SecretReference.

        Args:
            file_path: Path to the file containing the reference
            line_number: Line number where the reference was found
            secret_name: Name of the secret being referenced
        """
        self.file_path = file_path
        self.line_number = line_number
        self.secret_name = secret_name

    def __repr__(self) -> str:
        """Return string representation.

        Note: This logs secret names (keys), not secret values (credentials).
        This is intentional for validation reporting.
        """
        # pylint: disable=logging-sensitive-data
        # nosec B608  # noqa: S608
        return f"{self.file_path}:{self.line_number}: !secret {self.secret_name}"


def find_secret_references(yaml_file: Path) -> list[SecretReference]:
    """Find all !secret references in a YAML file.

    Args:
        yaml_file: Path to the YAML file to scan

    Returns:
        List of SecretReference objects found in the file
    """
    references: list[SecretReference] = []
    secret_pattern = re.compile(r"!secret\s+(\w+)")

    try:
        with open(yaml_file, encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                # Skip comments
                if line.strip().startswith("#"):
                    continue

                matches = secret_pattern.findall(line)
                # pylint: disable=logging-sensitive-data
                # nosec B608  # noqa: S608
                for secret_name in matches:
                    # Note: secret_name is a key reference, not a credential value
                    references.append(SecretReference(yaml_file, line_num, secret_name))

    except Exception as e:
        print(f"Warning: Could not read {yaml_file}: {e}", file=sys.stderr)

    return references


def load_secrets_file(secrets_file: Path) -> set[str]:
    """Load secret names from secrets.yaml or secrets.yaml.example.

    Args:
        secrets_file: Path to the secrets file

    Returns:
        Set of secret names defined in the file
    """
    secrets: set[str] = set()

    if not secrets_file.exists():
        return secrets

    try:
        with open(secrets_file, encoding="utf-8") as f:
            content = yaml.safe_load(f)

        if content is None:
            return secrets

        if isinstance(content, dict):
            secrets = set(content.keys())

    except yaml.YAMLError as e:
        print(f"Error: Could not parse {secrets_file}: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"Error: Could not read {secrets_file}: {e}", file=sys.stderr)
        sys.exit(2)

    return secrets


def scan_directory(directory: Path, pattern: str = "**/*.yaml") -> list[SecretReference]:
    """Recursively scan directory for !secret references.

    Args:
        directory: Directory to scan
        pattern: Glob pattern for files to scan

    Returns:
        List of all SecretReference objects found
    """
    all_references: list[SecretReference] = []

    for yaml_file in directory.glob(pattern):
        # Skip storage and backup directories
        if any(
            skip in yaml_file.parts
            for skip in [".storage", "backups", "deps", ".cloud", "tts"]
        ):
            continue

        references = find_secret_references(yaml_file)
        all_references.extend(references)

    return all_references


def validate_secrets(
    config_dir: Path, secrets_file: Path | None = None, verbose: bool = False
) -> tuple[list[SecretReference], set[str]]:
    """Validate that all secret references have corresponding definitions.

    Args:
        config_dir: Path to the config directory
        secrets_file: Path to secrets.yaml (if None, auto-detect)
        verbose: Print detailed information

    Returns:
        Tuple of (missing_references, defined_secrets)
    """
    # Auto-detect secrets file
    if secrets_file is None:
        secrets_file = config_dir / "secrets.yaml"
        if not secrets_file.exists():
            secrets_file = config_dir / "secrets.yaml.example"

    if verbose:
        print(f"Scanning configuration directory: {config_dir}")
        print(f"Using secrets file: {secrets_file}")

    # Load defined secrets
    defined_secrets = load_secrets_file(secrets_file)
    if verbose:
        print(f"Found {len(defined_secrets)} defined secrets")

    # Find all secret references
    all_references = scan_directory(config_dir)
    if verbose:
        print(f"Found {len(all_references)} secret references")

    # Check for missing secrets (comparing key names, not credential values)
    missing_references: list[SecretReference] = []
    # pylint: disable=logging-sensitive-data
    # nosec B608  # noqa: S608
    for ref in all_references:
        if ref.secret_name not in defined_secrets:
            missing_references.append(ref)

    return missing_references, defined_secrets


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for missing secrets, 2 for errors)
    """
    parser = argparse.ArgumentParser(
        description="Validate !secret references in Home Assistant configuration"
    )
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path(__file__).parent.parent / "config",
        help="Path to Home Assistant config directory (default: ../config)",
    )
    parser.add_argument(
        "--secrets-file",
        type=Path,
        help="Path to secrets.yaml file (default: auto-detect)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Print detailed information (missing secret locations; secret names are not shown)"
    )
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        default=True,
        help="Exit with code 1 if missing secrets are found (default: true)",
    )

    args = parser.parse_args()

    if not args.config_dir.exists():
        print(f"Error: Config directory not found: {args.config_dir}", file=sys.stderr)
        return 2

    # Validate secrets
    missing_references, defined_secrets = validate_secrets(
        args.config_dir, args.secrets_file, args.verbose
    )

    # Report results
    if missing_references:
        print("\n❌ Missing secrets found:\n", file=sys.stderr)
        # pylint: disable=logging-sensitive-data
        # nosec B608  # noqa: S608
        # Intentionally logging secret names (keys), not values
        # Only print missing secret references in verbose mode to avoid leaking secret names
        if args.verbose:
            for ref in sorted(
                missing_references, key=lambda r: (r.secret_name, str(r.file_path))
            ):
                # Only log location of missing secret, not the secret name.
                print(f"  {ref.file_path}:{ref.line_number}", file=sys.stderr)

        print(f"\n{len(missing_references)} missing secret(s)", file=sys.stderr)

        missing_secret_names = sorted(
            {ref.secret_name for ref in missing_references}
        )
        # Print missing secret names only in verbose mode; otherwise, redact/omit
        if args.verbose:
            print(
                f"\nNumber of unique missing secret names: {len(missing_secret_names)}",
                file=sys.stderr,
            )
        else:
            print(f"\n(Missing secret names hidden; run with --verbose to show)", file=sys.stderr)

        if args.fail_on_missing:
            return 1
    else:
        print("✅ All secret references are defined")
        if args.verbose:
            print(f"   Total references: {len(scan_directory(args.config_dir))}")
            print(f"   Defined secrets: {len(defined_secrets)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
