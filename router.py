from collections.abc import Iterator
from typing import Any

import logging
logging.basicConfig(level=logging.INFO)


class Serve_ollama_cloud:
    def serve(self, input: dict[str, Any]) -> str:
        from providers.ollama_cloud_client import OllamaCloudClient
        reply = OllamaCloudClient().chat(input)
        return reply.choices[0].message.content

    def stream(self, input: dict[str, Any]) -> Iterator[str]:
        from providers.ollama_cloud_client import OllamaCloudClient
        return OllamaCloudClient().stream_chat(input)


class Serve_ollama_local:
    def serve(self, input: dict[str, Any]) -> str:
        from providers.ollama_local_client import OllamaLocalClient
        reply = OllamaLocalClient().chat(input)
        return reply.choices[0].message.content

    def stream(self, input: dict[str, Any]) -> Iterator[str]:
        from providers.ollama_local_client import OllamaLocalClient
        return OllamaLocalClient().stream_chat(input)


class Serve_gemini:
    def serve(self, input: dict[str, Any]) -> str:
        from providers.gemini_client import GeminiClient
        reply = GeminiClient().chat(input)
        return reply.choices[0].message.content

    def stream(self, input: dict[str, Any]) -> Iterator[str]:
        from providers.gemini_client import GeminiClient
        return GeminiClient().stream_chat(input)


class Serve_openrouter:
    def serve(self, input: dict[str, Any]) -> str:
        from providers.openrouter_client import OpenrouterClient
        reply = OpenrouterClient().chat(input)
        return reply.choices[0].message.content

    def stream(self, input: dict[str, Any]) -> Iterator[str]:
        from providers.openrouter_client import OpenrouterClient
        return OpenrouterClient().stream_chat(input)


class Router:
    def route(self, input: dict[str, Any]) -> str:
        if input["provider"] == "ollama_cloud":
            logging.info("ROUTER: Routing request to OLLAMA CLOUD.")
            return Serve_ollama_cloud().serve(input)

        elif input["provider"] == "ollama_local":
            logging.info("ROUTER: Routing request to OLLAMA LOCAL.")
            return Serve_ollama_local().serve(input)

        elif input["provider"] == "gemini":
            logging.info("ROUTER: Routing request to GEMINI.")
            return Serve_gemini().serve(input)

        else:
            logging.info("ROUTER: Routing request to OPENROUTER.")
            return Serve_openrouter().serve(input)

    def stream_route(self, input: dict[str, Any]) -> Iterator[str]:
        if input["provider"] == "ollama_cloud":
            logging.info("ROUTER: Streaming request to OLLAMA CLOUD.")
            return Serve_ollama_cloud().stream(input)

        elif input["provider"] == "ollama_local":
            logging.info("ROUTER: Streaming request to OLLAMA LOCAL.")
            return Serve_ollama_local().stream(input)

        elif input["provider"] == "gemini":
            logging.info("ROUTER: Streaming request to GEMINI.")
            return Serve_gemini().stream(input)

        else:
            logging.info("ROUTER: Streaming request to OPENROUTER.")
            return Serve_openrouter().stream(input)