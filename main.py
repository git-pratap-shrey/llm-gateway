from uuid6 import uuid7

from fastapi import FastAPI
from typing import Any, Dict

from validation import Schema
from worker import Worker
from router import Router
from result_store.result_store import Result_store
    
app = FastAPI()

@app.post("/api/async")
def process_async(data: Schema) -> dict[str, str]: # validation fails return an 422 error automatically by fastapi.

    job_id = str(uuid7())

    Worker().produce_message({
        "job_id": job_id,
        "input":  data.model_dump(),
        "status": "queued",
        "output" : None
    })

    return {"job_id": job_id,
            "message": "Job queued successfully."}



@app.post("/api/sync")
def process_sync(data: Schema) -> Any:
    data_dict = data.model_dump()

    response = Router().route(data_dict)

    return response



@app.get("/{job_id}")
def get_item(job_id: str) -> dict[str, Any]:
    return Result_store().check_status(job_id)


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