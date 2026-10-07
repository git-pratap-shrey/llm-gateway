import logging
from collections.abc import Iterator
from typing import Any

from openai import OpenAI

from config import OLLAMA_CLOUD_BASE_URL
from providers.key_pool import KeyPool


class OllamaCloudClient:
    def __init__(self, key_pool: KeyPool) -> None:
        self._key_pool = key_pool
        self._base_url = OLLAMA_CLOUD_BASE_URL

    def chat(self, input: dict[str, Any]) -> Any:
        try:
            logging.info("OllamaCloud: Sending request.")
            client = OpenAI(
                api_key=self._key_pool.get_next(),
                base_url=self._base_url,
            )
            response = client.chat.completions.create(
                model=input["model"],
                messages=input["messages"],
                **(input.get("parameters") or {}),
            )
            logging.info("OllamaCloud: Response received.")
            return response
        except Exception as e:
            logging.error(f"OllamaCloud: Error: {e}")
            raise

    def stream_chat(self, input: dict[str, Any]) -> Iterator[str]:
        try:
            logging.info("OllamaCloud: Opening streaming request.")
            client = OpenAI(
                api_key=self._key_pool.get_next(),
                base_url=self._base_url,
            )
            with client.chat.completions.create(
                model=input["model"],
                messages=input["messages"],
                stream=True,
                **(input.get("parameters") or {}),
            ) as stream:
                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
            logging.info("OllamaCloud: Stream complete.")
        except Exception as e:
            logging.error(f"OllamaCloud: Stream error: {e}")
            raise
