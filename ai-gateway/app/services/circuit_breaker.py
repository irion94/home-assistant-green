"""Circuit breaker pattern for external API calls (Phase 7).

Prevents cascading failures by opening the circuit after threshold failures.
Automatically attempts recovery after timeout period.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Circuit broken, requests fail fast
- HALF_OPEN: Testing recovery, single request allowed
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Any, TypeVar
import logging

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"          # Normal operation
    OPEN = "open"              # Failing, reject requests
    HALF_OPEN = "half_open"    # Testing recovery


class CircuitBreakerOpen(Exception):
    """Exception raised when circuit breaker is open."""

    pass


class CircuitBreaker:
    """Circuit breaker to prevent cascading failures.

    Usage:
        breaker = CircuitBreaker(name="brave_search", failure_threshold=5)
        result = await breaker.call(my_async_function, arg1, arg2)
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        name: str = "circuit"
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            name: Circuit name for logging
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name

        self.failures = 0
        self.last_failure_time: datetime | None = None
        self.state = CircuitState.CLOSED

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute function with circuit breaker protection.

        Args:
            func: Async function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Function result

        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Original exception from func (when circuit is closed/half-open)
        """
        # Check if circuit should transition to HALF_OPEN
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(f"[{self.name}] Circuit transitioning to HALF_OPEN")
                self.state = CircuitState.HALF_OPEN
            else:
                elapsed = self._elapsed_since_failure()
                remaining = self.recovery_timeout - (elapsed or 0)
                raise CircuitBreakerOpen(
                    f"Circuit breaker OPEN for {self.name} "
                    f"(retry in {remaining:.0f}s)"
                )

        try:
            # Call the function
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e

    def _on_success(self):
        """Handle successful call."""
        if self.failures > 0:
            logger.info(
                f"[{self.name}] Call succeeded after {self.failures} failures"
            )

        self.failures = 0
        self.last_failure_time = None

        if self.state == CircuitState.HALF_OPEN:
            logger.info(f"[{self.name}] Circuit recovered, transitioning to CLOSED")
            self.state = CircuitState.CLOSED

    def _on_failure(self):
        """Handle failed call."""
        self.failures += 1
        self.last_failure_time = datetime.now()

        logger.warning(
            f"[{self.name}] Failure {self.failures}/{self.failure_threshold}"
        )

        if self.failures >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                logger.error(
                    f"[{self.name}] Circuit breaker OPENED "
                    f"({self.failures} failures, will retry in {self.recovery_timeout}s)"
                )
                self.state = CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should attempt recovery.

        Returns:
            True if enough time has passed since last failure
        """
        if not self.last_failure_time:
            return False

        elapsed = self._elapsed_since_failure()
        if elapsed is None:
            return False

        return elapsed > self.recovery_timeout

    def _elapsed_since_failure(self) -> float | None:
        """Get seconds elapsed since last failure.

        Returns:
            Seconds elapsed or None if no failures
        """
        if not self.last_failure_time:
            return None

        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed

    def get_status(self) -> dict[str, Any]:
        """Get current circuit breaker status.

        Returns:
            Status dictionary with state, failures, and timing info
        """
        status: dict[str, Any] = {
            "name": self.name,
            "state": self.state.value,
            "failures": self.failures,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
        }

        if self.last_failure_time:
            elapsed = self._elapsed_since_failure()
            status["last_failure"] = self.last_failure_time.isoformat()
            status["elapsed_seconds"] = elapsed

            if self.state == CircuitState.OPEN and elapsed is not None:
                remaining = self.recovery_timeout - elapsed
                status["retry_in_seconds"] = max(0, remaining)

        return status

    def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        logger.info(f"[{self.name}] Manually resetting circuit breaker")
        self.failures = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
