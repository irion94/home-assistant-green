"""Dynamic adapter loading from various sources.

Provides utilities to load backend adapters from:
- Local filesystem paths (development)
- Installed Python packages
- Git repositories (production)
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

from app.core.interfaces.backend import HomeAutomationBackend
from app.core.registry.backend_registry import BackendRegistry
from app.core.registry.config import BackendConfig

logger = logging.getLogger(__name__)


class AdapterLoader:
    """Load backend adapters from various sources.

    Supports loading adapters from:
    - builtin: Built-in adapters in app.adapters package
    - path: Local filesystem path
    - package: Installed Python package
    - git: Git repository (cloned to local path)

    Example:
        >>> # Load from config
        >>> config = BackendConfig.from_env()
        >>> await AdapterLoader.load_from_config(config)

        >>> # Load from path directly
        >>> AdapterLoader.load_from_path(Path("../home-assistant-service"))
    """

    # Directory for git-cloned adapters
    ADAPTERS_DIR = Path("/app/adapters")

    @classmethod
    async def load_from_config(cls, config: BackendConfig) -> None:
        """Load adapter based on configuration.

        Main entry point for loading adapters. Routes to appropriate
        loader based on config.source.

        Args:
            config: Backend configuration

        Raises:
            ValueError: If source type is invalid
            ImportError: If adapter cannot be loaded
        """
        logger.info(f"Loading adapter '{config.adapter}' from source '{config.source}'")

        if config.source == "builtin":
            cls.load_builtin(config.adapter)
        elif config.source == "path":
            if not config.path:
                raise ValueError("path required for source='path'")
            cls.load_from_path(Path(config.path))
        elif config.source == "package":
            if not config.package:
                raise ValueError("package required for source='package'")
            cls.load_from_package(config.package)
        elif config.source == "git":
            if not config.git_url:
                raise ValueError("git_url required for source='git'")
            await cls.load_from_git(config.git_url, config.git_ref, config.adapter)
        else:
            raise ValueError(f"Invalid source type: {config.source}")

    @classmethod
    def load_builtin(cls, adapter_name: str) -> None:
        """Load a built-in adapter.

        Built-in adapters are located in app.adapters.{adapter_name}
        and must provide a register() function or export an adapter class.

        Args:
            adapter_name: Name of the built-in adapter (e.g., 'mock')

        Raises:
            ImportError: If adapter module not found
        """
        module_path = f"app.adapters.{adapter_name}"

        try:
            module = importlib.import_module(module_path)
            logger.info(f"Loaded built-in adapter module: {module_path}")

            # Try to call register() if it exists
            if hasattr(module, "register"):
                module.register()
                logger.debug(f"Called {module_path}.register()")
            # Otherwise look for adapter class and register it
            elif hasattr(module, "adapter") and hasattr(module.adapter, cls._get_adapter_class_name(adapter_name)):
                adapter_class = getattr(module.adapter, cls._get_adapter_class_name(adapter_name))
                BackendRegistry.register(adapter_name, adapter_class)
            else:
                # Auto-register if the module exports an adapter class
                cls._auto_register_from_module(module, adapter_name)

        except ImportError as e:
            raise ImportError(f"Built-in adapter '{adapter_name}' not found: {e}") from e

    @classmethod
    def load_from_path(cls, adapter_path: Path) -> None:
        """Load adapter from local filesystem path.

        The adapter directory must contain either:
        - A Python package with __init__.py
        - A setup.py or pyproject.toml

        Args:
            adapter_path: Path to adapter directory

        Raises:
            FileNotFoundError: If path doesn't exist
            ImportError: If adapter cannot be loaded
        """
        adapter_path = adapter_path.resolve()

        if not adapter_path.exists():
            raise FileNotFoundError(f"Adapter path not found: {adapter_path}")

        logger.info(f"Loading adapter from path: {adapter_path}")

        # Add to sys.path if not already there
        path_str = str(adapter_path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)
            logger.debug(f"Added {path_str} to sys.path")

        # Find the adapter package name
        package_name = cls._find_package_name(adapter_path)
        if not package_name:
            raise ImportError(f"Could not determine package name for {adapter_path}")

        # Import and register
        try:
            module = importlib.import_module(package_name)

            # Call register() if available
            if hasattr(module, "register"):
                module.register()
            else:
                # Try to find and register adapter class automatically
                adapter_name = adapter_path.name.replace("-", "_")
                cls._auto_register_from_module(module, adapter_name)

            logger.info(f"Loaded adapter from path: {package_name}")

        except ImportError as e:
            raise ImportError(f"Failed to import adapter from {adapter_path}: {e}") from e

    @classmethod
    def load_from_package(cls, package_name: str) -> None:
        """Load adapter from installed Python package.

        Args:
            package_name: Python package name (e.g., 'home_assistant_service')

        Raises:
            ImportError: If package not found
        """
        try:
            module = importlib.import_module(package_name)

            if hasattr(module, "register"):
                module.register()
            else:
                # Derive adapter name from package
                adapter_name = package_name.split(".")[-1]
                cls._auto_register_from_module(module, adapter_name)

            logger.info(f"Loaded adapter from package: {package_name}")

        except ImportError as e:
            raise ImportError(f"Adapter package '{package_name}' not found: {e}") from e

    @classmethod
    async def load_from_git(
        cls,
        git_url: str,
        git_ref: str = "main",
        adapter_name: str | None = None,
    ) -> Path:
        """Clone/update adapter from git repository.

        Clones the repository to ADAPTERS_DIR and loads it.
        If already cloned, updates to the specified ref.

        Args:
            git_url: Git repository URL
            git_ref: Branch, tag, or commit hash
            adapter_name: Override adapter name (default: extracted from URL)

        Returns:
            Path to cloned adapter

        Raises:
            RuntimeError: If git operations fail
            ImportError: If adapter cannot be loaded
        """
        # Extract adapter name from URL if not provided
        if not adapter_name:
            adapter_name = cls._extract_name_from_url(git_url)

        adapter_path = cls.ADAPTERS_DIR / adapter_name
        cls.ADAPTERS_DIR.mkdir(parents=True, exist_ok=True)

        if adapter_path.exists():
            logger.info(f"Updating adapter {adapter_name} from {git_url}#{git_ref}")
            await cls._git_update(adapter_path, git_ref)
        else:
            logger.info(f"Cloning adapter {adapter_name} from {git_url}#{git_ref}")
            await cls._git_clone(git_url, adapter_path, git_ref)

        # Install dependencies if requirements.txt exists
        requirements_file = adapter_path / "requirements.txt"
        if requirements_file.exists():
            await cls._pip_install(requirements_file)

        # Load the adapter
        cls.load_from_path(adapter_path)

        return adapter_path

    @classmethod
    async def _git_clone(cls, url: str, path: Path, ref: str) -> None:
        """Clone a git repository.

        Args:
            url: Repository URL
            path: Target directory
            ref: Branch/tag/commit

        Raises:
            RuntimeError: If clone fails
        """
        cmd = ["git", "clone", "--branch", ref, "--depth", "1", url, str(path)]
        await cls._run_command(cmd)

    @classmethod
    async def _git_update(cls, path: Path, ref: str) -> None:
        """Update a git repository to a specific ref.

        Args:
            path: Repository directory
            ref: Target branch/tag/commit

        Raises:
            RuntimeError: If update fails
        """
        # Fetch latest
        await cls._run_command(["git", "-C", str(path), "fetch", "--depth", "1", "origin", ref])
        # Checkout the ref
        await cls._run_command(["git", "-C", str(path), "checkout", ref])
        # Pull if on a branch
        await cls._run_command(
            ["git", "-C", str(path), "pull", "--ff-only"],
            ignore_errors=True,  # May fail if detached HEAD
        )

    @classmethod
    async def _pip_install(cls, requirements_file: Path) -> None:
        """Install Python dependencies from requirements.txt.

        Args:
            requirements_file: Path to requirements.txt

        Raises:
            RuntimeError: If pip install fails
        """
        logger.info(f"Installing dependencies from {requirements_file}")
        cmd = [sys.executable, "-m", "pip", "install", "-r", str(requirements_file), "-q"]
        await cls._run_command(cmd)

    @classmethod
    async def _run_command(
        cls,
        cmd: list[str],
        ignore_errors: bool = False,
    ) -> tuple[str, str]:
        """Run a shell command asynchronously.

        Args:
            cmd: Command and arguments
            ignore_errors: If True, don't raise on non-zero exit

        Returns:
            Tuple of (stdout, stderr)

        Raises:
            RuntimeError: If command fails and ignore_errors=False
        """
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        stdout_str = stdout.decode() if stdout else ""
        stderr_str = stderr.decode() if stderr else ""

        if proc.returncode != 0 and not ignore_errors:
            raise RuntimeError(
                f"Command failed: {' '.join(cmd)}\n"
                f"Exit code: {proc.returncode}\n"
                f"stderr: {stderr_str}"
            )

        return stdout_str, stderr_str

    @classmethod
    def _find_package_name(cls, path: Path) -> str | None:
        """Find Python package name in a directory.

        Looks for:
        1. pyproject.toml [project].name
        2. setup.py name argument
        3. Directory with __init__.py matching path name

        Args:
            path: Directory to search

        Returns:
            Package name or None
        """
        # Check for pyproject.toml
        pyproject = path / "pyproject.toml"
        if pyproject.exists():
            try:
                import tomllib

                with open(pyproject, "rb") as f:
                    data = tomllib.load(f)
                name = data.get("project", {}).get("name")
                if name:
                    return name.replace("-", "_")
            except (ImportError, Exception):
                pass

        # Look for a package directory
        for item in path.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                return item.name

        # Fall back to directory name
        return path.name.replace("-", "_")

    @classmethod
    def _extract_name_from_url(cls, url: str) -> str:
        """Extract adapter name from git URL.

        Args:
            url: Git repository URL

        Returns:
            Adapter name (e.g., 'home-assistant-service')
        """
        # Remove trailing slash and .git
        name = url.rstrip("/")
        if name.endswith(".git"):
            name = name[:-4]
        # Get the repository name
        name = name.split("/")[-1]
        return name

    @classmethod
    def _get_adapter_class_name(cls, adapter_name: str) -> str:
        """Convert adapter name to class name.

        Args:
            adapter_name: Adapter name (e.g., 'home_assistant')

        Returns:
            Class name (e.g., 'HomeAssistantBackend')
        """
        parts = adapter_name.replace("-", "_").split("_")
        return "".join(p.capitalize() for p in parts) + "Backend"

    @classmethod
    def _auto_register_from_module(cls, module: Any, adapter_name: str) -> None:
        """Auto-register adapter class from module.

        Looks for a class ending in 'Backend' that implements
        HomeAutomationBackend protocol.

        Args:
            module: Imported module
            adapter_name: Name to register under
        """
        # Look for adapter class
        for attr_name in dir(module):
            if attr_name.endswith("Backend"):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and isinstance(attr, HomeAutomationBackend):
                    BackendRegistry.register(adapter_name, attr)
                    logger.info(f"Auto-registered {attr_name} as '{adapter_name}'")
                    return

        logger.warning(f"Could not auto-register adapter from module {module.__name__}")
