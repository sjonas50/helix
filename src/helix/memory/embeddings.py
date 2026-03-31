"""Embedding generation for semantic memory search.

Uses OpenAI text-embedding-3-large (1536 dimensions).
Fallback to mock embeddings in development when API key not set.
"""

import structlog
from openai import AsyncOpenAI

from helix.config import get_settings

logger = structlog.get_logger()


async def embed_text(
    text: str, model: str = "text-embedding-3-large"
) -> list[float]:
    """Generate embedding vector for a single text."""
    settings = get_settings()
    if not settings.openai_api_key:
        logger.warning(
            "embeddings.no_api_key", msg="Using zero vector for development"
        )
        return [0.0] * 1536

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.embeddings.create(input=[text], model=model)
    return response.data[0].embedding


async def embed_batch(
    texts: list[str],
    model: str = "text-embedding-3-large",
    batch_size: int = 2048,
) -> list[list[float]]:
    """Generate embeddings for multiple texts with batching."""
    settings = get_settings()
    if not settings.openai_api_key:
        logger.warning(
            "embeddings.no_api_key", msg="Using zero vectors for development"
        )
        return [[0.0] * 1536 for _ in texts]

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = await client.embeddings.create(input=batch, model=model)
        all_embeddings.extend([d.embedding for d in response.data])

    return all_embeddings
