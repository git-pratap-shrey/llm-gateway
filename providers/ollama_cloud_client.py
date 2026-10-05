import logging
import os
from collections.abc import Iterator
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from config import OLLAMA_CLOUD_BASE_URL, OLLAMA_API_KEY_ENV

load_dotenv()


class OllamaCloudClient:
    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=os.environ[OLLAMA_API_KEY_ENV],
            base_url=OLLAMA_CLOUD_BASE_URL,
        )

    def chat(self, input: dict[str, Any]) -> Any:
        try:
            logging.info("OllamaCloud: Sending request.")
            response = self.client.chat.completions.create(
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
            with self.client.chat.completions.create(
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
