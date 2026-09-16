import pytest
from unittest.mock import patch, MagicMock

from router import Router

def test_route_ollama():
    with patch("router.Serve_ollama.serve") as mock_serve:
        mock_serve.return_value = "Mocked Ollama Response"
        
        message = {
            "provider": "ollama",
            "model": "gemma",
            "messages": [{"role": "user", "content": "Hello"}]
        }
        
        response = Router().route(message)
        
        assert response == "Mocked Ollama Response"
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

def test_serve_ollama_internal():
    from router import Serve_ollama
    
    with patch("providers.ollama_client.OllamaClient") as mock_client_class:
        mock_client_instance = MagicMock()
        mock_client_class.return_value = mock_client_instance
        mock_client_instance.chat.return_value = {"message": {"content": "Ollama chat content"}}
        
        message = {
            "provider": "ollama",
            "model": "gemma",
            "messages": [{"role": "user", "content": "Hello"}]
        }
        
        response = Serve_ollama().serve(message)
        
        assert response == "Ollama chat content"
        mock_client_instance.chat.assert_called_once_with(model="gemma", messages=[{"role": "user", "content": "Hello"}])
