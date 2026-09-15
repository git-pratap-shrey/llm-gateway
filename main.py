import json

from fastapi import FastAPI

from validation import Schema
from worker import Worker
from router import router
    
app = FastAPI()


@app.post("/api/async")
async def process_async(data: Schema): # validation fails return an 422 error automatically by fastapi.
    data_json = data.model_dump_json()

    worker = Worker()
    worker.produce_message(data_json)

    return "Successfully added to the queue for processing"

@app.post("/api/sync")
async def process_sync(data: Schema):
    data_json = data.model_dump_json()

    response = router().route(json.loads(data_json))

    return response

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