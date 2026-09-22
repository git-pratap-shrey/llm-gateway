from uuid6 import uuid7
from fastapi import FastAPI, HTTPException
from typing import Any, Dict

from validation import Schema
from worker import Worker
from router import Router
from result_store.result_store import Result_store
from utils.logging_utils import job_log_file

app = FastAPI()

@app.post("/api/async")
def process_async(data: Schema) -> dict[str, str]: # validation fails return an 422 error automatically by fastapi.

    job_id = str(uuid7())

    with job_log_file(job_id):
        # Insert record into DB before producing to queue
        Result_store().create_job(job_id, data.model_dump())

        try:
            Worker().produce_message({
                "job_id": job_id,
                "input":  data.model_dump(),
                "status": "queued",
                "output" : None
            })
        except HTTPException as e:
            # Mark as failed if queueing fails
            Result_store().update_job(job_id, status="failed", output=None)
            raise e

    return {"job_id": job_id,
            "message": "Job queued successfully."}


@app.post("/api/sync")
def process_sync(data: Schema) -> Any:
    data_dict = data.model_dump()
    job_id = f"sync_{uuid7()}"

    with job_log_file(job_id):
        response = Router().route(data_dict)

    return response


@app.get("/{job_id}")
def get_item(job_id: str) -> dict[str, Any] | None:
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
