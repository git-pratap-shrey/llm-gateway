from fastapi import FastAPI
app = FastAPI()

from providers.ollama_client import OllamaClient
from validation import Schema


@app.post("/api")
async def receive_data(data: Schema): # validation fails return an 422 error automatically by fastapi.
    data_dict = data.model_dump()

    # process_request(data_dict)


    return "Successfully added to the queue for processing"


# def process_request(data_dict : dict):
#     if data_dict["provider"] == "ollama":
#         model = data_dict["model"]
#         messages = data_dict["messages"]

#         client = OllamaClient()
#         client.chat(model, messages)


# USAGE : uv run uvicorn main:app --reload

# curl -X POST http://localhost:8000/api \
#   -H "Content-Type: application/json" \
#   -d '{
#     "provider": "ollama",
#     "model": "gemma4:cloud",
#     "messages": [
#       {
#         "role": "user",
#         "content": "Hello"
#       }
#     ]
#   }'