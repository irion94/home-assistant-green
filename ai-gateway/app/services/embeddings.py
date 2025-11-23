"""Embedding generation service using Ollama."""

from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using Ollama."""

    def __init__(self) -> None:
        """Initialize embedding service."""
        self.ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
        self.dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "384"))
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        client = await self._get_client()

        try:
            response = await client.post(
                f"{self.ollama_url}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text,
                },
            )
            response.raise_for_status()
            data = response.json()
            embedding = data.get("embedding", [])

            if not embedding:
                logger.error("Empty embedding returned from Ollama")
                raise ValueError("Empty embedding returned")

            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            return embedding

        except httpx.HTTPError as e:
            logger.error(f"HTTP error generating embedding: {e}")
            raise
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            embedding = await self.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings

    async def is_available(self) -> bool:
        """Check if embedding model is available."""
        client = await self._get_client()

        try:
            # Check if model is loaded
            response = await client.get(f"{self.ollama_url}/api/tags")
            response.raise_for_status()
            data = response.json()

            models = data.get("models", [])
            model_names = [m.get("name", "").split(":")[0] for m in models]

            if self.model.split(":")[0] in model_names:
                return True

            logger.warning(
                f"Embedding model '{self.model}' not found. "
                f"Available models: {model_names}"
            )
            return False

        except Exception as e:
            logger.error(f"Error checking embedding model availability: {e}")
            return False

    async def pull_model(self) -> bool:
        """Pull the embedding model if not available."""
        client = await self._get_client()

        try:
            logger.info(f"Pulling embedding model: {self.model}")
            response = await client.post(
                f"{self.ollama_url}/api/pull",
                json={"name": self.model},
                timeout=300.0,  # 5 minutes for model download
            )
            response.raise_for_status()
            logger.info(f"Successfully pulled embedding model: {self.model}")
            return True

        except Exception as e:
            logger.error(f"Error pulling embedding model: {e}")
            return False


# Singleton instance
embedding_service = EmbeddingService()
