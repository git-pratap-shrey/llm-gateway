import logging
import time
from collections.abc import Iterator
from typing import Any

from openai import OpenAI

from config import GEMINI_BASE_URL
from providers.key_pool import KeyPool


class GeminiClient:
    def __init__(self, key_pool: KeyPool) -> None:
        self._key_pool = key_pool
        self._base_url = GEMINI_BASE_URL
        logging.debug(f"GeminiClient: Initialized with base URL {self._base_url}")

    def chat(self, input: dict[str, Any]) -> Any:
        model = input.get("model", "unknown")
        messages_count = len(input.get("messages", []))
        try:
            logging.info(f"Gemini: Sending request for model '{model}' with {messages_count} message(s).")
            logging.info("Gemini: Sending request.")
            start_time = time.perf_counter()
            client = OpenAI(
                api_key=self._key_pool.get_next(),
                base_url=self._base_url,
            )
            response = client.chat.completions.create(
                model=input["model"],
                messages=input["messages"],
                **(input.get("parameters") or {}),
            )
            elapsed = time.perf_counter() - start_time
            usage = getattr(response, "usage", None)
            usage_str = f" [tokens: prompt={getattr(usage, 'prompt_tokens', 'N/A')}, completion={getattr(usage, 'completion_tokens', 'N/A')}]" if usage else ""
            logging.info(f"Gemini: Response received in {elapsed:.2f}s{usage_str}.")
            logging.info("Gemini: Response received.")
            return response
        except Exception as e:
            logging.error(f"Gemini: Error for model '{model}': {e}")
            logging.error(f"Gemini: Error: {e}")
            raise

    def stream_chat(self, input: dict[str, Any]) -> Iterator[str]:
        model = input.get("model", "unknown")
        messages_count = len(input.get("messages", []))
        try:
            logging.info(f"Gemini: Opening streaming request for model '{model}' with {messages_count} message(s).")
            logging.info("Gemini: Opening streaming request.")
            start_time = time.perf_counter()
            chunk_count = 0
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
                        chunk_count += 1
                        yield delta
            elapsed = time.perf_counter() - start_time
            logging.info(f"Gemini: Stream complete ({chunk_count} chunk(s) in {elapsed:.2f}s).")
            logging.info("Gemini: Stream complete.")
        except Exception as e:
            logging.error(f"Gemini: Stream error for model '{model}': {e}")
            logging.error(f"Gemini: Stream error: {e}")
            raise

    def list_models(self) -> Any:
        try:
            logging.info("Gemini: Fetching list of available models.")
            client = OpenAI(
                api_key=self._key_pool.get_next(),
                base_url=self._base_url,
            )
            models = client.models.list()
            data = getattr(models, "data", [])
            logging.info(f"Gemini: Successfully retrieved {len(data)} model(s).")
            return models
        except Exception as e:
            logging.error(f"Gemini: list_models error: {e}")
            return []