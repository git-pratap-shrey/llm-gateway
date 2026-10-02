from uuid6 import uuid7
from fastapi import FastAPI, HTTPException
from typing import Any

from validation import Schema
from worker import Worker
from router import Router
from result_store.result_store import Result_store
from utils.logging_utils import job_log_file

import logging
logging.basicConfig(level=logging.INFO)

app = FastAPI()

@app.post("/api/async")
def process_async(data: Schema) -> dict[str, str]: # validation fails return an 422 error automatically by fastapi.

    job_id = str(uuid7()) #UUID 7 for time queryable id.

    with job_log_file(job_id):
        logging.info(f"FASTAPI:Request validity checked.")
        logging.info(f"FASTAPI: Async job id generated: {job_id}.")
        logging.info(f"FASTAPI: Received input: {data.model_dump()}.")

        # Insert record into DB before producing to queue
        Result_store().create_job(job_id, data.model_dump())

        try:
            Worker().produce_message({
                "job_id": job_id,
                "input":  data.model_dump(),
                "status": "queued",
                "output" : None
            })

            logging.info(f"FASTAPI: Job queued successfully.")

        except HTTPException as e:

            # Mark as failed if queueing fails.
            Result_store().update_job(job_id, status="failed", output=None)

            raise e # raise since failure shouldn't be 200 OK.

    return {"job_id": job_id,
            "message": "Job queued successfully."}


@app.post("/api/sync")
def process_sync(data: Schema) -> Any:
    data_dict = data.model_dump()
    job_id = f"sync_{uuid7()}" #UUID 7 for time queryable id.


    with job_log_file(job_id):
        logging.info(f"FASTAPI:Request validity checked.")
        logging.info(f"FASTAPI: Sync job id generated: {job_id}.")
        logging.info(f"FASTAPI: Received input: {data_dict}.")

        try:
            response = Router().route(data_dict)
        except Exception as e:
            logging.error(f"FASTAPI: Sync job failed: {e}")
            raise HTTPException(status_code=500, detail={"job_id": job_id, "message": "Job processing failed."})

        logging.info(f"FASTAPI: Job processed successfully.")
        logging.info(f"FASTAPI: Output generated: {response}.")

    return response


@app.get("/{job_id}")
def get_item(job_id: str) -> dict[str, Any]:
    result = Result_store().check_status(job_id)
    if result is None:
        raise HTTPException(status_code=404, detail={"job_id": job_id, "message": "Job not found."})
    return result

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
