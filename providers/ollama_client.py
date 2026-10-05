import logging
import os

from collections.abc import Iterator
from dotenv import load_dotenv
from ollama import Client, ResponseError
from typing import Any

load_dotenv()

class OllamaClient:
    def __init__(self) -> None:
        self.client = Client(
            host="https://ollama.com",
            headers={
                "Authorization": f"Bearer {os.environ['OLLAMA_API_KEY']}"
            }
        )

    def chat(self, input: dict[str, Any]) -> Any:
        try:
            logging.info(f"Ollama: Sending input to Ollama.")
            response = self.client.chat(
                model=input["model"],
                messages=input["messages"]
            )

            logging.info(f"Ollama: Response received.")
            return response

        except ResponseError as e:
            logging.error(f"Ollama: Error occurred: {e}")
            raise

    def stream_chat(self, input: dict[str, Any]) -> Iterator[str]:
        try:
            logging.info("Ollama: Opening streaming request.")
            for chunk in self.client.chat(
                model=input["model"],
                messages=input["messages"],
                stream=True,
            ):
                token = chunk["message"]["content"]
                if token:
                    yield token
            logging.info("Ollama: Stream complete.")
        except ResponseError as e:
            logging.error(f"Ollama: Stream error: {e}")
            raise


# todo : parameters, persisitent client, failures