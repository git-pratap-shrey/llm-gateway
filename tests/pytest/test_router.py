import pytest
from unittest.mock import patch, MagicMock

from router import Router, Serve_ollama_cloud, Serve_gemini, Serve_openrouter


# ---------------------------------------------------------------------------
# Router.route dispatch
# ---------------------------------------------------------------------------

def test_route_ollama_cloud():
    with patch("router.Serve_ollama_cloud.serve") as mock_serve:
        mock_serve.return_value = "Mocked Ollama Cloud Response"

        message = {
            "provider": "ollama_cloud",
            "model": "gemma4:cloud",
            "messages": [{"role": "user", "content": "Hello"}]
        }

        response = Router().route(message)

        assert response == "Mocked Ollama Cloud Response"
        mock_serve.assert_called_once_with(message)


def test_route_gemini():
    with patch("router.Serve_gemini.serve") as mock_serve:
        mock_serve.return_value = "Mocked Gemini Response"

        message = {
            "provider": "gemini",
            "model": "gemini-pro",
            "messages": [{"role": "user", "content": "Hello"}]
        }

        response = Router().route(message)

        assert response == "Mocked Gemini Response"
        mock_serve.assert_called_once_with(message)


def test_route_openrouter():
    with patch("router.Serve_openrouter.serve") as mock_serve:
        mock_serve.return_value = "Mocked Openrouter Response"

        message = {
            "provider": "openrouter",
            "model": "mistralai/mixtral-8x7b",
            "messages": [{"role": "user", "content": "Hello"}]
        }

        response = Router().route(message)

        assert response == "Mocked Openrouter Response"
        mock_serve.assert_called_once_with(message)


def test_route_unknown_provider_falls_through_to_openrouter():
    """
    The router has no explicit unknown-provider guard; it falls through to
    Serve_openrouter as the default 'else' branch.
    """
    with patch("router.Serve_openrouter.serve") as mock_serve:
        mock_serve.return_value = "Openrouter fallback"

        message = {
            "provider": "unknown",
            "model": "gemma",
            "messages": [{"role": "user", "content": "Hello"}]
        }

        response = Router().route(message)
        assert response == "Openrouter fallback"
        mock_serve.assert_called_once_with(message)


# ---------------------------------------------------------------------------
# Router.stream_route dispatch
# ---------------------------------------------------------------------------

def test_stream_route_ollama_cloud():
    with patch("router.Serve_ollama_cloud.stream") as mock_stream:
        mock_stream.return_value = iter(["tok1", "tok2"])

        message = {
            "provider": "ollama_cloud",
            "model": "gemma4:cloud",
            "messages": [{"role": "user", "content": "Hello"}]
        }

        result = list(Router().stream_route(message))
        assert result == ["tok1", "tok2"]
        mock_stream.assert_called_once_with(message)


def test_stream_route_gemini():
    with patch("router.Serve_gemini.stream") as mock_stream:
        mock_stream.return_value = iter(["g1", "g2"])

        message = {
            "provider": "gemini",
            "model": "gemma-pro",
            "messages": [{"role": "user", "content": "Hello"}]
        }

        result = list(Router().stream_route(message))
        assert result == ["g1", "g2"]


def test_stream_route_openrouter():
    with patch("router.Serve_openrouter.stream") as mock_stream:
        mock_stream.return_value = iter(["or1"])

        message = {
            "provider": "openrouter",
            "model": "mistralai/mixtral-8x7b",
            "messages": [{"role": "user", "content": "Hello"}]
        }

        result = list(Router().stream_route(message))
        assert result == ["or1"]


# ---------------------------------------------------------------------------
# Serve_ollama_cloud internal unit test
# ---------------------------------------------------------------------------

def test_serve_ollama_cloud_internal():
    with patch("providers.ollama_cloud_client.OllamaCloudClient") as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance

        mock_reply = MagicMock()
        mock_reply.choices[0].message.content = "OllamaCloud chat content"
        mock_client_instance.chat.return_value = mock_reply

        message = {
            "provider": "ollama_cloud",
            "model": "gemma4:cloud",
            "messages": [{"role": "user", "content": "Hello"}]
        }

        response = Serve_ollama_cloud().serve(message)

        assert response == "OllamaCloud chat content"
        mock_client_instance.chat.assert_called_once_with(message)


# ---------------------------------------------------------------------------
# Serve_gemini internal unit test
# ---------------------------------------------------------------------------

def test_serve_gemini_internal():
    with patch("providers.gemini_client.GeminiClient") as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance

        # Gemini now uses .choices[0].message.content (OpenAI-style)
        mock_reply = MagicMock()
        mock_reply.choices[0].message.content = "Gemini chat content"
        mock_client_instance.chat.return_value = mock_reply

        message = {
            "provider": "gemini",
            "model": "gemini-pro",
            "messages": [{"role": "user", "content": "Hello"}]
        }

        response = Serve_gemini().serve(message)

        assert response == "Gemini chat content"
        mock_client_instance.chat.assert_called_once_with(message)


# ---------------------------------------------------------------------------
# Serve_openrouter internal unit test
# ---------------------------------------------------------------------------

def test_serve_openrouter_internal():
    with patch("providers.openrouter_client.OpenrouterClient") as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance

        mock_reply = MagicMock()
        mock_reply.choices[0].message.content = "Openrouter chat content"
        mock_client_instance.chat.return_value = mock_reply

        message = {
            "provider": "openrouter",
            "model": "mistralai/mixtral-8x7b",
            "messages": [{"role": "user", "content": "Hello"}]
        }

        response = Serve_openrouter().serve(message)

        assert response == "Openrouter chat content"
        mock_client_instance.chat.assert_called_once_with(message)
