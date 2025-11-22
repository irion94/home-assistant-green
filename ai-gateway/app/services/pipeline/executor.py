"""Parallel pipeline executor for intent recognition.

Runs multiple recognizers in parallel, returns first confident result.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import HAAction
    from app.services.entity_discovery import EntityDiscovery
    from app.services.intent_matcher import IntentMatcher
    from app.services.llm_client import LLMClient
    from app.services.llm_cache import LLMCache
    from app.services.ollama_client import OllamaClient
    from app.services.pattern_learner import PatternLearner

logger = logging.getLogger(__name__)


@dataclass
class IntentResult:
    """Result from an intent recognizer with confidence score."""

    action: HAAction | None
    confidence: float  # 0.0 to 1.0
    source: str  # "pattern", "ollama", "openai"
    latency_ms: float  # Time taken in milliseconds


class IntentPipeline:
    """Cascading intent recognition pipeline.

    Runs pattern matcher and LLM in parallel.
    Returns first result that meets confidence threshold.
    """

    def __init__(
        self,
        intent_matcher: IntentMatcher,
        llm_client: LLMClient,
        confidence_threshold: float = 0.8,
        entity_discovery: EntityDiscovery | None = None,
        llm_cache: LLMCache | None = None,
        pattern_learner: PatternLearner | None = None,
    ):
        """Initialize pipeline.

        Args:
            intent_matcher: Fast pattern-based matcher
            llm_client: LLM client (Ollama/OpenAI)
            confidence_threshold: Minimum confidence to accept (0.0-1.0)
            entity_discovery: Optional entity discovery for dynamic matching
            llm_cache: Optional cache for LLM results
            pattern_learner: Optional learner for auto-improving patterns
        """
        self.intent_matcher = intent_matcher
        self.llm_client = llm_client
        self.confidence_threshold = confidence_threshold
        self.entity_discovery = entity_discovery
        self.llm_cache = llm_cache
        self.pattern_learner = pattern_learner

    async def process(self, text: str) -> IntentResult:
        """Process text through pipeline.

        Runs pattern matcher and LLM in parallel.
        Returns pattern result immediately if confident.
        Falls back to LLM if pattern not confident.

        Args:
            text: User command text

        Returns:
            Best IntentResult from available recognizers
        """
        import time as time_module
        start = time_module.perf_counter()

        # 1. Check learned patterns first (instant)
        if self.pattern_learner:
            learned_match = self.pattern_learner.match(text)
            if learned_match:
                entity_id, service, confidence = learned_match
                from app.models import HAAction
                action = HAAction(
                    action="call_service",
                    service=service,
                    entity_id=entity_id,
                    data={},
                )
                latency = (time_module.perf_counter() - start) * 1000
                logger.info(
                    f"Pipeline: learned pattern match "
                    f"(confidence={confidence:.2f}, latency={latency:.1f}ms)"
                )
                return IntentResult(
                    action=action,
                    confidence=confidence,
                    source="learned_pattern",
                    latency_ms=latency,
                )

        # 2. Check LLM cache (instant)
        if self.llm_cache:
            cached = self.llm_cache.get(text)
            if cached:
                action, confidence = cached
                latency = (time_module.perf_counter() - start) * 1000
                logger.info(
                    f"Pipeline: cache hit "
                    f"(confidence={confidence:.2f}, latency={latency:.1f}ms)"
                )
                return IntentResult(
                    action=action,
                    confidence=confidence,
                    source="cache",
                    latency_ms=latency,
                )

        # 3. Start both recognizers in parallel
        pattern_task = asyncio.create_task(self._run_pattern_matcher(text))
        llm_task = asyncio.create_task(self._run_llm(text))

        # Wait for pattern matcher first (much faster)
        pattern_result = await pattern_task

        # If pattern matcher is confident, cancel LLM and return
        if pattern_result.action and pattern_result.confidence >= self.confidence_threshold:
            llm_task.cancel()
            logger.info(
                f"Pipeline: pattern match accepted "
                f"(confidence={pattern_result.confidence:.2f}, latency={pattern_result.latency_ms:.0f}ms)"
            )
            return pattern_result

        # Wait for LLM result
        try:
            llm_result = await llm_task
        except asyncio.CancelledError:
            llm_result = IntentResult(
                action=None,
                confidence=0.0,
                source="ollama",
                latency_ms=0.0,
            )

        # Compare results and return best
        if llm_result.action and llm_result.confidence >= self.confidence_threshold:
            # Cache the successful LLM result
            if self.llm_cache:
                self.llm_cache.put(text, llm_result.action, llm_result.confidence)

            # Learn from high-confidence matches
            if self.pattern_learner:
                self.pattern_learner.learn(text, llm_result.action, llm_result.confidence)

            logger.info(
                f"Pipeline: LLM result accepted "
                f"(confidence={llm_result.confidence:.2f}, latency={llm_result.latency_ms:.0f}ms)"
            )
            return llm_result

        # Return pattern result if it has something, even with low confidence
        if pattern_result.action:
            logger.info(
                f"Pipeline: using pattern result with low confidence "
                f"(confidence={pattern_result.confidence:.2f})"
            )
            return pattern_result

        # Return LLM result as last resort
        if llm_result.action:
            logger.info(
                f"Pipeline: using LLM result with low confidence "
                f"(confidence={llm_result.confidence:.2f})"
            )
            return llm_result

        # Nothing worked
        logger.warning("Pipeline: no recognizer returned a valid result")
        return IntentResult(
            action=None,
            confidence=0.0,
            source="none",
            latency_ms=pattern_result.latency_ms + llm_result.latency_ms,
        )

    async def _run_pattern_matcher(self, text: str) -> IntentResult:
        """Run pattern matcher and return result with confidence.

        Args:
            text: User command text

        Returns:
            IntentResult with action and confidence
        """
        start = time.perf_counter()

        try:
            action, confidence = self.intent_matcher.match_with_confidence(text)
            latency = (time.perf_counter() - start) * 1000

            return IntentResult(
                action=action,
                confidence=confidence,
                source="pattern",
                latency_ms=latency,
            )
        except Exception as e:
            logger.error(f"Pattern matcher error: {e}")
            latency = (time.perf_counter() - start) * 1000
            return IntentResult(
                action=None,
                confidence=0.0,
                source="pattern",
                latency_ms=latency,
            )

    async def _run_llm(self, text: str) -> IntentResult:
        """Run LLM and return result with confidence.

        Uses dynamic entity matching if entity_discovery is available,
        otherwise falls back to static prompt.

        Args:
            text: User command text

        Returns:
            IntentResult with action and confidence
        """
        start = time.perf_counter()

        try:
            # Use dynamic entity matching if available
            if self.entity_discovery is not None:
                entities = await self.entity_discovery.get_entities()
                if entities:
                    # Check if client supports dynamic matching
                    from app.services.ollama_client import OllamaClient
                    from app.services.openai_client import OpenAIClient

                    if isinstance(self.llm_client, (OllamaClient, OpenAIClient)):
                        action, confidence = await self.llm_client.translate_command_dynamic(
                            text, entities
                        )
                        latency = (time.perf_counter() - start) * 1000
                        source = "openai_dynamic" if isinstance(self.llm_client, OpenAIClient) else "ollama_dynamic"
                        logger.info(f"LLM used dynamic entity matching ({len(entities)} entities)")
                        return IntentResult(
                            action=action,
                            confidence=confidence,
                            source=source,
                            latency_ms=latency,
                        )

            # Fall back to static prompt
            action, confidence = await self.llm_client.translate_command_with_confidence(text)
            latency = (time.perf_counter() - start) * 1000

            return IntentResult(
                action=action,
                confidence=confidence,
                source="ollama",
                latency_ms=latency,
            )
        except Exception as e:
            logger.error(f"LLM error: {e}")
            latency = (time.perf_counter() - start) * 1000
            return IntentResult(
                action=None,
                confidence=0.0,
                source="ollama",
                latency_ms=latency,
            )
