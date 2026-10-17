import os
from collections.abc import Iterator
from typing import Any

import logging
logging.basicConfig(level=logging.INFO)

from config import (
    OLLAMA_API_KEY_ENV,
    GEMINI_API_KEY_ENV,
    OPENROUTER_API_KEY_ENV,
)
from providers.key_pool import KeyPool


def _create_key_pool(env_var: str) -> KeyPool:
    """Create a KeyPool from comma-separated environment variable."""
    keys_str = os.environ.get(env_var, "")
    keys = [k.strip() for k in keys_str.split(",") if k.strip()]
    if not keys:
        logging.warning(f"ROUTER: No API keys configured for environment variable '{env_var}'.")
    else:
        logging.info(f"ROUTER: Initialized key pool for '{env_var}' with {len(keys)} key(s).")
    return KeyPool(keys)


# Lazy initialization: key pools are created on first access
# This allows tests to set env vars before pools are initialized
_ollama_key_pool: KeyPool | None = None
_gemini_key_pool: KeyPool | None = None
_openrouter_key_pool: KeyPool | None = None


def _get_ollama_key_pool() -> KeyPool:
    """Get or create the Ollama key pool."""
    global _ollama_key_pool
    if _ollama_key_pool is None:
        _ollama_key_pool = _create_key_pool(OLLAMA_API_KEY_ENV)
    return _ollama_key_pool


def _get_gemini_key_pool() -> KeyPool:
    """Get or create the Gemini key pool."""
    global _gemini_key_pool
    if _gemini_key_pool is None:
        _gemini_key_pool = _create_key_pool(GEMINI_API_KEY_ENV)
    return _gemini_key_pool


def _get_openrouter_key_pool() -> KeyPool:
    """Get or create the Openrouter key pool."""
    global _openrouter_key_pool
    if _openrouter_key_pool is None:
        _openrouter_key_pool = _create_key_pool(OPENROUTER_API_KEY_ENV)
    return _openrouter_key_pool


class Serve_ollama_cloud:
    def serve(self, input: dict[str, Any]) -> str:
        from providers.ollama_cloud_client import OllamaCloudClient
        model = input.get("model", "unknown")
        logging.debug(f"ROUTER: Serve_ollama_cloud handling request for model '{model}'.")
        reply = OllamaCloudClient(_get_ollama_key_pool()).chat(input)
        return reply.choices[0].message.content

    def stream(self, input: dict[str, Any]) -> Iterator[str]:
        from providers.ollama_cloud_client import OllamaCloudClient
        model = input.get("model", "unknown")
        logging.debug(f"ROUTER: Serve_ollama_cloud handling streaming request for model '{model}'.")
        return OllamaCloudClient(_get_ollama_key_pool()).stream_chat(input)





class Serve_gemini:
    def serve(self, input: dict[str, Any]) -> str:
        from providers.gemini_client import GeminiClient
        model = input.get("model", "unknown")
        logging.debug(f"ROUTER: Serve_gemini handling request for model '{model}'.")
        reply = GeminiClient(_get_gemini_key_pool()).chat(input)
        return reply.choices[0].message.content

    def stream(self, input: dict[str, Any]) -> Iterator[str]:
        from providers.gemini_client import GeminiClient
        model = input.get("model", "unknown")
        logging.debug(f"ROUTER: Serve_gemini handling streaming request for model '{model}'.")
        return GeminiClient(_get_gemini_key_pool()).stream_chat(input)


class Serve_openrouter:
    def serve(self, input: dict[str, Any]) -> str:
        from providers.openrouter_client import OpenrouterClient
        model = input.get("model", "unknown")
        logging.debug(f"ROUTER: Serve_openrouter handling request for model '{model}'.")
        reply = OpenrouterClient(_get_openrouter_key_pool()).chat(input)
        return reply.choices[0].message.content

    def stream(self, input: dict[str, Any]) -> Iterator[str]:
        from providers.openrouter_client import OpenrouterClient
        model = input.get("model", "unknown")
        logging.debug(f"ROUTER: Serve_openrouter handling streaming request for model '{model}'.")
        return OpenrouterClient(_get_openrouter_key_pool()).stream_chat(input)


class Router:
    def route(self, input: dict[str, Any]) -> str:
        provider = input.get("provider")
        model = input.get("model")
        if provider == "ollama_cloud":
            logging.info("ROUTER: Routing request to OLLAMA CLOUD.")
            logging.debug(f"ROUTER: Routing to OLLAMA CLOUD (model: {model}).")
            return Serve_ollama_cloud().serve(input)

        elif provider == "gemini":
            logging.info("ROUTER: Routing request to GEMINI.")
            logging.debug(f"ROUTER: Routing to GEMINI (model: {model}).")
            return Serve_gemini().serve(input)

        else:
            logging.info("ROUTER: Routing request to OPENROUTER.")
            logging.debug(f"ROUTER: Routing to OPENROUTER (provider: {provider}, model: {model}).")
            return Serve_openrouter().serve(input)

    def stream_route(self, input: dict[str, Any]) -> Iterator[str]:
        provider = input.get("provider")
        model = input.get("model")
        if provider == "ollama_cloud":
            logging.info("ROUTER: Streaming request to OLLAMA CLOUD.")
            logging.debug(f"ROUTER: Streaming with OLLAMA CLOUD (model: {model}).")
            return Serve_ollama_cloud().stream(input)

        elif provider == "gemini":
            logging.info("ROUTER: Streaming request to GEMINI.")
            logging.debug(f"ROUTER: Streaming with GEMINI (model: {model}).")
            return Serve_gemini().stream(input)

        else:
            logging.info("ROUTER: Streaming request to OPENROUTER.")
            logging.debug(f"ROUTER: Streaming with OPENROUTER (provider: {provider}, model: {model}).")
            return Serve_openrouter().stream(input)