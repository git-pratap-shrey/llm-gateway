import logging
import time
from collections.abc import Iterator
from typing import Any

from openai import OpenAI

from config import OLLAMA_CLOUD_BASE_URL, OLLAMA_CLOUD_TIMEOUT
from providers.key_pool import KeyPool


class OllamaCloudClient:
    def __init__(self, key_pool: KeyPool) -> None:
        self._key_pool = key_pool
        self._base_url = OLLAMA_CLOUD_BASE_URL
        self._timeout = OLLAMA_CLOUD_TIMEOUT
        logging.debug(f"OllamaCloudClient: Initialized with base URL {self._base_url}, timeout={self._timeout}s")

    def chat(self, input: dict[str, Any]) -> Any:
        model = input.get("model", "unknown")
        messages_count = len(input.get("messages", []))
        try:
            logging.info(f"OllamaCloud: Sending request for model '{model}' with {messages_count} message(s).")
            logging.info("OllamaCloud: Sending request.")
            start_time = time.perf_counter()
            client = OpenAI(
                api_key=self._key_pool.get_next(),
                base_url=self._base_url,
                timeout=self._timeout,
            )
            response = client.chat.completions.create(
                model=input["model"],
                messages=input["messages"],
                **(input.get("parameters") or {}),
            )
            elapsed = time.perf_counter() - start_time
            usage = getattr(response, "usage", None)
            usage_str = f" [tokens: prompt={getattr(usage, 'prompt_tokens', 'N/A')}, completion={getattr(usage, 'completion_tokens', 'N/A')}]" if usage else ""
            logging.info(f"OllamaCloud: Response received in {elapsed:.2f}s{usage_str}.")
            logging.info("OllamaCloud: Response received.")
            return response
        except Exception as e:
            logging.error(f"OllamaCloud: Error for model '{model}': {e}")
            logging.error(f"OllamaCloud: Error: {e}")
            raise

    def stream_chat(self, input: dict[str, Any]) -> Iterator[str]:
        model = input.get("model", "unknown")
        messages_count = len(input.get("messages", []))
        try:
            logging.info(f"OllamaCloud: Opening streaming request for model '{model}' with {messages_count} message(s).")
            logging.info("OllamaCloud: Opening streaming request.")
            start_time = time.perf_counter()
            chunk_count = 0
            client = OpenAI(
                api_key=self._key_pool.get_next(),
                base_url=self._base_url,
                timeout=self._timeout,
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
                        chunk_count += 1
                        yield delta
            elapsed = time.perf_counter() - start_time
            logging.info(f"OllamaCloud: Stream complete ({chunk_count} chunk(s) in {elapsed:.2f}s).")
            logging.info("OllamaCloud: Stream complete.")
        except Exception as e:
            logging.error(f"OllamaCloud: Stream error for model '{model}': {e}")
            logging.error(f"OllamaCloud: Stream error: {e}")
            raise
