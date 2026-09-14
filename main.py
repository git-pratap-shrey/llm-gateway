from fastapi import FastAPI

from validation import Schema
from worker import Worker
from router import router
    
app = FastAPI()


@app.post("/api/poll_send")
async def process_req(data: Schema): # validation fails return an 422 error automatically by fastapi.
    data_json = data.model_dump_json()

    worker = Worker()
    worker.produce_message(data_json)

    return "Successfully added to the queue for processing"

@app.post("/api/direct_send")
async def process_req(data: Schema):
    data_json = data.model_dump_json()

    return router().route(data_json)

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