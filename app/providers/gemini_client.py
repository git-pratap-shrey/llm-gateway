from google import genai
from google.genai import errors
from dotenv import load_dotenv

load_dotenv()

class GeminiClient:
    def __init__(self):
        self.client = genai.Client()

    def chat(self, model: str, messages: list[dict]):
        try:
            response = self.client.models.generate_content(
                model=model,
                contents=messages
            )
            print(response.text)

        except errors.APIError as e:
            print(f"gemini provider error ({e.code}): {e.message}")

    def list_models(self):
        try:
            models = self.client.models.list()
            return models
        except errors.APIError as e:
            print(f"gemini provider error ({e.code}): {e.message}")
            return []

# if not any(model.name == model_str for model in models):
#     print(f"Model '{model_str}' not found or unsupported")
#     exit()
