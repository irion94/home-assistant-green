"""Protocol definitions for home automation backends.

This module defines the abstract interfaces that all backend adapters
must implement. Using Protocol allows for structural subtyping,
making it easy to create new adapters without inheritance.
"""

from app.core.interfaces.backend import HomeAutomationBackend

__all__ = ["HomeAutomationBackend"]
