"""Unit tests for the provider client adapters.

All actual network calls (openai.OpenAI) are mocked so no real
API keys or running services are required.
"""
import os
from unittest.mock import MagicMock, patch, call

import pytest

# Provide dummy env vars so client constructors don't KeyError
os.environ.setdefault("OLLAMA_API_KEY", "test-ollama-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("OPENROUTER_API_KEY", "test-openrouter-key")


# ===========================================================================
# OllamaCloudClient
# ===========================================================================

class TestOllamaCloudClient:

    @pytest.fixture()
    def mock_key_pool(self):
        """Create a mock KeyPool that returns a test key."""
        from providers.key_pool import KeyPool
        mock_pool = MagicMock(spec=KeyPool)
        mock_pool.get_next.return_value = "test-api-key"
        return mock_pool

    @pytest.fixture()
    def mock_openai(self):
        with patch("providers.ollama_cloud_client.OpenAI") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            yield mock_instance

    def test_chat_returns_response(self, mock_openai, mock_key_pool):
        from providers.ollama_cloud_client import OllamaCloudClient

        mock_reply = MagicMock()
        mock_openai.chat.completions.create.return_value = mock_reply

        client = OllamaCloudClient(mock_key_pool)
        result = client.chat({"model": "gemma4:cloud", "messages": [{"role": "user", "content": "hi"}]})

        assert result is mock_reply
        mock_openai.chat.completions.create.assert_called_once_with(
            model="gemma4:cloud",
            messages=[{"role": "user", "content": "hi"}],
        )

    def test_chat_passes_parameters(self, mock_openai, mock_key_pool):
        from providers.ollama_cloud_client import OllamaCloudClient

        mock_openai.chat.completions.create.return_value = MagicMock()

        client = OllamaCloudClient(mock_key_pool)
        client.chat({
            "model": "gemma4:cloud",
            "messages": [],
            "parameters": {"temperature": 0.7, "max_tokens": 100},
        })

        kwargs = mock_openai.chat.completions.create.call_args.kwargs
        assert kwargs["temperature"] == 0.7
        assert kwargs["max_tokens"] == 100

    def test_chat_raises_on_error(self, mock_openai, mock_key_pool):
        from providers.ollama_cloud_client import OllamaCloudClient

        mock_openai.chat.completions.create.side_effect = RuntimeError("upstream down")

        with pytest.raises(RuntimeError, match="upstream down"):
            OllamaCloudClient(mock_key_pool).chat({"model": "gemma4:cloud", "messages": []})

    def test_stream_chat_yields_tokens(self, mock_openai, mock_key_pool):
        from providers.ollama_cloud_client import OllamaCloudClient

        chunk1 = MagicMock()
        chunk1.choices[0].delta.content = "Hello"
        chunk2 = MagicMock()
        chunk2.choices[0].delta.content = " world"
        chunk3 = MagicMock()
        chunk3.choices[0].delta.content = None  # empty delta — must be skipped

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=iter([chunk1, chunk2, chunk3]))
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_openai.chat.completions.create.return_value = mock_stream

        tokens = list(OllamaCloudClient(mock_key_pool).stream_chat({
            "model": "gemma4:cloud",
            "messages": [],
        }))

        assert tokens == ["Hello", " world"]

    def test_stream_chat_raises_on_error(self, mock_openai, mock_key_pool):
        from providers.ollama_cloud_client import OllamaCloudClient

        mock_openai.chat.completions.create.side_effect = RuntimeError("stream error")

        with pytest.raises(RuntimeError):
            list(OllamaCloudClient(mock_key_pool).stream_chat({"model": "gemma4:cloud", "messages": []}))


# ===========================================================================
# GeminiClient
# ===========================================================================

class TestGeminiClient:

    @pytest.fixture()
    def mock_key_pool(self):
        """Create a mock KeyPool that returns a test key."""
        from providers.key_pool import KeyPool
        mock_pool = MagicMock(spec=KeyPool)
        mock_pool.get_next.return_value = "test-api-key"
        return mock_pool

    @pytest.fixture()
    def mock_openai(self):
        with patch("providers.gemini_client.OpenAI") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            yield mock_instance

    def test_chat_returns_response(self, mock_openai, mock_key_pool):
        from providers.gemini_client import GeminiClient

        mock_reply = MagicMock()
        mock_openai.chat.completions.create.return_value = mock_reply

        result = GeminiClient(mock_key_pool).chat({"model": "gemma-4-31b-it", "messages": []})

        assert result is mock_reply

    def test_chat_passes_parameters(self, mock_openai, mock_key_pool):
        from providers.gemini_client import GeminiClient

        mock_openai.chat.completions.create.return_value = MagicMock()
        GeminiClient(mock_key_pool).chat({
            "model": "gemma-4-31b-it",
            "messages": [],
            "parameters": {"top_p": 0.9},
        })

        kwargs = mock_openai.chat.completions.create.call_args.kwargs
        assert kwargs["top_p"] == 0.9

    def test_chat_raises_on_error(self, mock_openai, mock_key_pool):
        from providers.gemini_client import GeminiClient

        mock_openai.chat.completions.create.side_effect = ValueError("bad request")

        with pytest.raises(ValueError):
            GeminiClient(mock_key_pool).chat({"model": "gemma-4-31b-it", "messages": []})

    def test_stream_chat_yields_tokens(self, mock_openai, mock_key_pool):
        from providers.gemini_client import GeminiClient

        chunk = MagicMock()
        chunk.choices[0].delta.content = "token"

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=iter([chunk]))
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_openai.chat.completions.create.return_value = mock_stream

        tokens = list(GeminiClient(mock_key_pool).stream_chat({"model": "gemma-4-31b-it", "messages": []}))
        assert tokens == ["token"]

    def test_list_models_returns_result(self, mock_openai, mock_key_pool):
        from providers.gemini_client import GeminiClient

        mock_openai.models.list.return_value = ["model-a", "model-b"]

        result = GeminiClient(mock_key_pool).list_models()
        assert result == ["model-a", "model-b"]

    def test_list_models_returns_empty_list_on_error(self, mock_openai, mock_key_pool):
        from providers.gemini_client import GeminiClient

        mock_openai.models.list.side_effect = RuntimeError("no models")

        result = GeminiClient(mock_key_pool).list_models()
        assert result == []


# ===========================================================================
# OpenrouterClient
# ===========================================================================

class TestOpenrouterClient:

    @pytest.fixture()
    def mock_key_pool(self):
        """Create a mock KeyPool that returns a test key."""
        from providers.key_pool import KeyPool
        mock_pool = MagicMock(spec=KeyPool)
        mock_pool.get_next.return_value = "test-api-key"
        return mock_pool

    @pytest.fixture()
    def mock_openai(self):
        with patch("providers.openrouter_client.OpenAI") as mock_cls:
            mock_instance = MagicMock()
            mock_cls.return_value = mock_instance
            yield mock_instance

    def test_chat_returns_response(self, mock_openai, mock_key_pool):
        from providers.openrouter_client import OpenrouterClient

        mock_reply = MagicMock()
        mock_openai.chat.completions.create.return_value = mock_reply

        result = OpenrouterClient(mock_key_pool).chat({"model": "meta-llama/llama-3", "messages": []})
        assert result is mock_reply

    def test_chat_passes_parameters(self, mock_openai, mock_key_pool):
        from providers.openrouter_client import OpenrouterClient

        mock_openai.chat.completions.create.return_value = MagicMock()
        OpenrouterClient(mock_key_pool).chat({
            "model": "meta-llama/llama-3",
            "messages": [],
            "parameters": {"temperature": 0.5, "frequency_penalty": 0.1},
        })

        kwargs = mock_openai.chat.completions.create.call_args.kwargs
        assert kwargs["temperature"] == 0.5
        assert kwargs["frequency_penalty"] == 0.1

    def test_chat_raises_on_error(self, mock_openai, mock_key_pool):
        from providers.openrouter_client import OpenrouterClient

        mock_openai.chat.completions.create.side_effect = ConnectionError("network error")

        with pytest.raises(ConnectionError):
            OpenrouterClient(mock_key_pool).chat({"model": "meta-llama/llama-3", "messages": []})

    def test_stream_chat_yields_tokens(self, mock_openai, mock_key_pool):
        from providers.openrouter_client import OpenrouterClient

        chunk = MagicMock()
        chunk.choices[0].delta.content = "stream-token"

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=iter([chunk]))
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_openai.chat.completions.create.return_value = mock_stream

        tokens = list(OpenrouterClient(mock_key_pool).stream_chat({"model": "meta-llama/llama-3", "messages": []}))
        assert tokens == ["stream-token"]

    def test_stream_chat_skips_empty_deltas(self, mock_openai, mock_key_pool):
        from providers.openrouter_client import OpenrouterClient

        chunks = []
        for content in ["a", None, "b", ""]:
            c = MagicMock()
            c.choices[0].delta.content = content
            chunks.append(c)

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=iter(chunks))
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_openai.chat.completions.create.return_value = mock_stream

        tokens = list(OpenrouterClient(mock_key_pool).stream_chat({"model": "meta-llama/llama-3", "messages": []}))
        # Only non-empty, non-None tokens should be yielded
        assert tokens == ["a", "b"]

    def test_stream_chat_raises_on_error(self, mock_openai, mock_key_pool):
        from providers.openrouter_client import OpenrouterClient

        mock_openai.chat.completions.create.side_effect = RuntimeError("stream fail")

        with pytest.raises(RuntimeError):
            list(OpenrouterClient(mock_key_pool).stream_chat({"model": "meta-llama/llama-3", "messages": []}))

