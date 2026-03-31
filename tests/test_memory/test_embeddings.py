"""Tests for embedding generation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from helix.memory.embeddings import embed_batch, embed_text


@pytest.mark.asyncio
async def test_embed_text_no_api_key():
    """Returns zero vector when no OpenAI API key is configured."""
    with patch("helix.memory.embeddings.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(openai_api_key="")
        result = await embed_text("hello world")
    assert len(result) == 1536
    assert all(v == 0.0 for v in result)


@pytest.mark.asyncio
async def test_embed_text_with_mock():
    """Calls OpenAI embeddings API with correct parameters."""
    fake_embedding = [0.1] * 1536
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=fake_embedding)]

    mock_client = AsyncMock()
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)

    with (
        patch("helix.memory.embeddings.get_settings") as mock_settings,
        patch("helix.memory.embeddings.AsyncOpenAI", return_value=mock_client),
    ):
        mock_settings.return_value = MagicMock(openai_api_key="sk-test-key")
        result = await embed_text("test input", model="text-embedding-3-large")

    mock_client.embeddings.create.assert_awaited_once_with(
        input=["test input"], model="text-embedding-3-large"
    )
    assert result == fake_embedding


@pytest.mark.asyncio
async def test_embed_batch_no_api_key():
    """Returns zero vectors for batch when no API key."""
    with patch("helix.memory.embeddings.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(openai_api_key="")
        result = await embed_batch(["a", "b", "c"])
    assert len(result) == 3
    assert all(len(v) == 1536 for v in result)


@pytest.mark.asyncio
async def test_embed_batch_with_mock():
    """Calls OpenAI embeddings API with batching."""
    fake_embeddings = [[0.1] * 1536, [0.2] * 1536]
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=e) for e in fake_embeddings]

    mock_client = AsyncMock()
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)

    with (
        patch("helix.memory.embeddings.get_settings") as mock_settings,
        patch("helix.memory.embeddings.AsyncOpenAI", return_value=mock_client),
    ):
        mock_settings.return_value = MagicMock(openai_api_key="sk-test-key")
        result = await embed_batch(["text1", "text2"], batch_size=10)

    mock_client.embeddings.create.assert_awaited_once()
    assert len(result) == 2
