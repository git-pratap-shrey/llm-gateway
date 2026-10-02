import logging
from openrouter import OpenRouter
import os

from dotenv import load_dotenv
from typing import Any
load_dotenv()

class OpenrouterClient: 
    def __init__(self) -> None:
        self.client = OpenRouter(
            api_key=os.getenv("OPENROUTER_API_KEY")
        )

    def chat(self, input: dict[str, Any]) -> Any:
        try:
            logging.info(f"Openrouter: Sending input to Openrouter.")
            response = self.client.chat.send(
                model=input["model"],
                messages=input["messages"]
            )
            logging.info(f"Openrouter: Response received.")
            return response

        except Exception as e:
            logging.error(f"Openrouter: Provider error: {e}")
            raise