from google import genai
from google.genai import errors, types
from dotenv import load_dotenv

load_dotenv()

class GeminiClient:
    def __init__(self):
        self.client = genai.Client()

    def chat(self, model: str, messages: list[dict]) -> str:
        try:
            contents = [
                types.Content(
                    role=message["role"],
                    parts=[types.Part(text=message["content"])]
                )
                for message in messages
            ]

            response = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        disable=True
                    )
                )
            )
            return response

        except errors.APIError as e:
            print(f"gemini provider error ({e.code}): {e.message}")

    def list_models(self):
        try:
            models = self.client.models.list()
            return models
        except errors.APIError as e:
            print(f"gemini provider error ({e.code}): {e.message}")
            return []