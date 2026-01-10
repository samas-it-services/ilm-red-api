"""Embedding Service for generating text embeddings.

Uses OpenAI's text-embedding-3-small model (1536 dimensions) for
semantic search and RAG.

Principle P2: Chunks are for thinking (AI understanding).
"""

import logging
from typing import Protocol

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# Default embedding model (1536 dimensions)
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536


class EmbeddingProvider(Protocol):
    """Protocol for embedding providers."""

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        ...


class OpenAIEmbeddingService:
    """Generate embeddings using OpenAI API.

    Uses text-embedding-3-small for cost-effective semantic search.
    Supports both single text and batch embedding.

    Usage:
        service = OpenAIEmbeddingService(api_key="sk-...")
        embedding = await service.embed("Hello world")
        embeddings = await service.embed_batch(["Hello", "World"])
    """

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_EMBEDDING_MODEL,
    ):
        """Initialize embedding service.

        Args:
            api_key: OpenAI API key.
            model: Embedding model to use.
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def embed(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Text to embed.

        Returns:
            Embedding vector (1536 floats).

        Raises:
            Exception: If API call fails.
        """
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    async def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 100,
    ) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed.
            batch_size: Max texts per API call (default 100).

        Returns:
            List of embedding vectors.

        Raises:
            Exception: If API call fails.
        """
        if not texts:
            return []

        all_embeddings = []

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]

            try:
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=batch,
                )
                # Sort by index to ensure correct order
                sorted_data = sorted(response.data, key=lambda x: x.index)
                all_embeddings.extend([d.embedding for d in sorted_data])
            except Exception as e:
                logger.error(f"Batch embedding failed: {e}")
                raise

        return all_embeddings


class MockEmbeddingService:
    """Mock embedding service for testing.

    Returns zero vectors of correct dimension.
    """

    def __init__(self, dimensions: int = EMBEDDING_DIMENSIONS):
        self.dimensions = dimensions

    async def embed(self, text: str) -> list[float]:
        """Return zero vector."""
        return [0.0] * self.dimensions

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Return zero vectors."""
        return [[0.0] * self.dimensions for _ in texts]


def create_embedding_service(api_key: str | None = None) -> EmbeddingProvider:
    """Factory function to create embedding service.

    Args:
        api_key: OpenAI API key. If None, returns mock service.

    Returns:
        Embedding service instance.
    """
    if api_key:
        return OpenAIEmbeddingService(api_key=api_key)
    return MockEmbeddingService()
