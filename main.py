from fastapi import FastAPI

from validation import Schema
from worker import Worker
    
app = FastAPI()


@app.post("/api")
async def receive_data(data: Schema): # validation fails return an 422 error automatically by fastapi.
    data_json = data.model_dump_json()

    worker = Worker()
    worker.produce_message(data_json)

    return "Successfully added to the queue for processing"


# USAGE : uv run python -m uvicorn main:app --reload

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