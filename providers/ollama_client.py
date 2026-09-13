import os

from dotenv import load_dotenv
from ollama import Client, ResponseError

load_dotenv()

class OllamaClient:
    def __init__(self):
        self.client = Client(
            host="https://ollama.com",
            headers={
                "Authorization": f"Bearer {os.environ['OLLAMA_API_KEY']}"
            }
        )

    def chat(self, model : str, messages : list[dict]):
        try:
            response = self.client.chat(
                model=model,
                messages=messages
            )

            print(response.message.content)

        except ResponseError as e:
            print(f"Ollama error: {e}")


# todo : parameters, persisitent client, failures