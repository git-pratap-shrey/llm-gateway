from google import genai
from google.genai import errors
from dotenv import load_dotenv

load_dotenv()

client = genai.Client()

model_str = "gemini-5"
models = client.models.list()

if not any(model.name == model_str for model in models):
    print(f"Model '{model_str}' not found or unsupported")
    exit()


try:
    response = client.models.generate_content(
        model=model_str,
        contents="Hello!"
    )
    print(response.text)

except errors.APIError as e:
    print(f"gemini provider error ({e.code}): {e.message}")