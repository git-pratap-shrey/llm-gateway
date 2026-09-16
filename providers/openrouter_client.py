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

    def chat(self, model: str, messages: list[dict[str, Any]]) -> Any:
        try:
            response = self.client.chat.send(
                model=model,
                messages=messages
            )
            return response

        except Exception as e:
            print(f"openrouter error: {e}")