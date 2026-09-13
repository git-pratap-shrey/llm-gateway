from openrouter import OpenRouter
import os


from dotenv import load_dotenv

load_dotenv()

client = OpenRouter(
    api_key=os.getenv("OPENROUTER_API_KEY")
)

model = "google/gemma-4-31b-it"

try:
    response = client.chat.send(
        model=model,
        messages=[
            {"role": "user", "content": "hi"}
        ]
    )

    print(response.choices[0].message.content)

except Exception as e:
    print(f"openrouter error: {e}")