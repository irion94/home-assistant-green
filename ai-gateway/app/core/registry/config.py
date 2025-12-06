"""Backend configuration models.

Defines configuration for backend adapters, including source type
and backend-specific settings.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class BackendConfig(BaseModel):
    """Configuration for a home automation backend adapter.

    Specifies which adapter to use and how to load it. The adapter
    can be loaded from various sources:

    - builtin: Built-in adapters (mock, homeassistant if bundled)
    - package: Installed Python package
    - path: Local filesystem path (for development)
    - git: Git repository URL (for production)

    Attributes:
        adapter: Backend adapter name (e.g., 'homeassistant', 'mock')
        source: How to load the adapter
        path: Filesystem path (for source='path')
        package: Python package name (for source='package')
        git_url: Git repository URL (for source='git')
        git_ref: Git branch/tag/commit (for source='git')
        config: Backend-specific configuration

    Examples:
        >>> # Use built-in mock adapter
        >>> BackendConfig(adapter="mock", source="builtin")

        >>> # Load from local path for development
        >>> BackendConfig(
        ...     adapter="homeassistant",
        ...     source="path",
        ...     path="../home-assistant-service",
        ...     config={"base_url": "http://localhost:8123", "token": "xxx"}
        ... )

        >>> # Load from git for production
        >>> BackendConfig(
        ...     adapter="homeassistant",
        ...     source="git",
        ...     git_url="https://github.com/yourorg/home-assistant-service.git",
        ...     git_ref="v1.0.0",
        ...     config={"base_url": "http://homeassistant:8123", "token": "xxx"}
        ... )
    """

    adapter: str = Field(
        ...,
        description="Backend adapter name",
        examples=["mock", "homeassistant", "openhab"],
    )

    source: Literal["builtin", "package", "path", "git"] = Field(
        default="builtin",
        description="How to load the adapter",
    )

    path: str | None = Field(
        default=None,
        description="Filesystem path (for source='path')",
    )

    package: str | None = Field(
        default=None,
        description="Python package name (for source='package')",
    )

    git_url: str | None = Field(
        default=None,
        description="Git repository URL (for source='git')",
    )

    git_ref: str = Field(
        default="main",
        description="Git branch/tag/commit (for source='git')",
    )

    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Backend-specific configuration",
    )

    @field_validator("path")
    @classmethod
    def validate_path_for_source(cls, v: str | None, info: Any) -> str | None:
        """Validate path is provided when source='path'."""
        if info.data.get("source") == "path" and not v:
            raise ValueError("path is required when source='path'")
        return v

    @field_validator("package")
    @classmethod
    def validate_package_for_source(cls, v: str | None, info: Any) -> str | None:
        """Validate package is provided when source='package'."""
        if info.data.get("source") == "package" and not v:
            raise ValueError("package is required when source='package'")
        return v

    @field_validator("git_url")
    @classmethod
    def validate_git_url_for_source(cls, v: str | None, info: Any) -> str | None:
        """Validate git_url is provided when source='git'."""
        if info.data.get("source") == "git" and not v:
            raise ValueError("git_url is required when source='git'")
        return v

    @classmethod
    def from_env(cls) -> BackendConfig:
        """Create configuration from environment variables.

        Reads configuration from these environment variables:
        - BACKEND_ADAPTER: Adapter name (default: 'mock')
        - BACKEND_SOURCE: Source type (default: 'builtin')
        - BACKEND_PATH: Path for source='path'
        - BACKEND_PACKAGE: Package name for source='package'
        - BACKEND_GIT_URL: Git URL for source='git'
        - BACKEND_GIT_REF: Git ref for source='git'
        - BACKEND_CONFIG: JSON string with backend-specific config

        Returns:
            BackendConfig populated from environment
        """
        import json
        import os

        config_json = os.getenv("BACKEND_CONFIG", "{}")
        try:
            backend_config = json.loads(config_json)
        except json.JSONDecodeError:
            backend_config = {}

        return cls(
            adapter=os.getenv("BACKEND_ADAPTER", "mock"),
            source=os.getenv("BACKEND_SOURCE", "builtin"),  # type: ignore
            path=os.getenv("BACKEND_PATH"),
            package=os.getenv("BACKEND_PACKAGE"),
            git_url=os.getenv("BACKEND_GIT_URL"),
            git_ref=os.getenv("BACKEND_GIT_REF", "main"),
            config=backend_config,
        )

    class Config:
        """Pydantic model configuration."""

        json_schema_extra = {
            "examples": [
                {
                    "adapter": "mock",
                    "source": "builtin",
                    "config": {"latency_ms": 100},
                },
                {
                    "adapter": "homeassistant",
                    "source": "git",
                    "git_url": "https://github.com/yourorg/home-assistant-service.git",
                    "git_ref": "v1.0.0",
                    "config": {
                        "base_url": "http://homeassistant:8123",
                        "token": "your-token",
                    },
                },
            ]
        }
