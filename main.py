from fastapi import FastAPI
from os import getenv
from dotenv import load_dotenv
load_dotenv()

from google import genai
client = genai.Client(api_key=getenv("GEMINI_API_KEY"))

app = FastAPI()

@app.post("/data")
async def receive_data(data: dict):
    word = data["word"]

    interaction = client.interactions.create(
        model="gemma-4-26b-a4b-it",
        input=word
    )

    return {"message": interaction.output_text}