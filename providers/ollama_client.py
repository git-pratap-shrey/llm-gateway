import logging
import os

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
            response = self.client.chat(
                model=input["model"],
                messages=input["messages"]
            )

            return response

        except ResponseError as e:
            logging.error(f"Ollama error: {e}")


# todo : parameters, persisitent client, failures