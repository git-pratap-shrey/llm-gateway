import logging
from google import genai
from google.genai import errors, types
from dotenv import load_dotenv
from typing import Any

load_dotenv()

class GeminiClient:
    def __init__(self) -> None:
        self.client = genai.Client()

    def chat(self, input: dict[str, Any]) -> Any:
        try:
            contents = [
                types.Content(
                    role=message["role"],
                    parts=[types.Part(text=message["content"])]
                )
                for message in input["messages"]
            ]

            response = self.client.models.generate_content(
                model=input["model"],
                contents=contents,
                config=types.GenerateContentConfig(
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    )
                )
            )
            return response

        except errors.APIError as e:
            logging.error(f"gemini provider error ({e.code}): {e.message}")

    def list_models(self) -> Any:
        try:
            models = self.client.models.list()
            return models
        except errors.APIError as e:
            logging.error(f"gemini provider error ({e.code}): {e.message}")
            return []