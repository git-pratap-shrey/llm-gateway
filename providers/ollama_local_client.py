import logging
import os
from collections.abc import Iterator
from typing import Any

from dotenv import load_dotenv
from openai import NotFoundError, OpenAI

from config import OLLAMA_LOCAL_BASE_URL

load_dotenv()


class OllamaModelNotAvailableError(Exception):
    """Raised when the requested model is not present on the local Ollama instance."""

    def __init__(self, model: str) -> None:
        self.model = model
        super().__init__(
            f"Model '{model}' is not available on the local Ollama instance. "
            f"Pull it first with: ollama pull {model}"
        )


class OllamaLocalClient:
    def __init__(self) -> None:
        self.client = OpenAI(
            api_key="ollama",           # local Ollama requires no real auth
            base_url=OLLAMA_LOCAL_BASE_URL,
        )

    def chat(self, input: dict[str, Any]) -> Any:
        try:
            logging.info(f"OllamaLocal: Sending request (model={input['model']!r}).")
            response = self.client.chat.completions.create(
                model=input["model"],
                messages=input["messages"],
                **(input.get("parameters") or {}),
            )
            logging.info("OllamaLocal: Response received.")
            return response
        except NotFoundError:
            logging.error(f"OllamaLocal: Model '{input['model']}' not found locally.")
            raise OllamaModelNotAvailableError(input["model"])
        except Exception as e:
            logging.error(f"OllamaLocal: Error: {e}")
            raise

    def stream_chat(self, input: dict[str, Any]) -> Iterator[str]:
        try:
            logging.info(f"OllamaLocal: Opening streaming request (model={input['model']!r}).")
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
            logging.info("OllamaLocal: Stream complete.")
        except NotFoundError:
            logging.error(f"OllamaLocal: Model '{input['model']}' not found locally.")
            raise OllamaModelNotAvailableError(input["model"])
        except Exception as e:
            logging.error(f"OllamaLocal: Stream error: {e}")
            raise
