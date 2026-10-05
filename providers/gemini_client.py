import logging
import os
from collections.abc import Iterator
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from config import GEMINI_BASE_URL, GEMINI_API_KEY_ENV

load_dotenv()


class GeminiClient:
    def __init__(self) -> None:
        self.client = OpenAI(
            api_key=os.environ[GEMINI_API_KEY_ENV],
            base_url=GEMINI_BASE_URL,
        )

    def chat(self, input: dict[str, Any]) -> Any:
        try:
            logging.info("Gemini: Sending request.")
            response = self.client.chat.completions.create(
                model=input["model"],
                messages=input["messages"],
                **(input.get("parameters") or {}),
            )
            logging.info("Gemini: Response received.")
            return response
        except Exception as e:
            logging.error(f"Gemini: Error: {e}")
            raise

    def stream_chat(self, input: dict[str, Any]) -> Iterator[str]:
        try:
            logging.info("Gemini: Opening streaming request.")
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
            logging.info("Gemini: Stream complete.")
        except Exception as e:
            logging.error(f"Gemini: Stream error: {e}")
            raise

    def list_models(self) -> Any:
        try:
            return self.client.models.list()
        except Exception as e:
            logging.error(f"Gemini: list_models error: {e}")
            return []