from contextlib import asynccontextmanager
from uuid6 import uuid7
from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Any

from validation import Schema
from worker import Worker
from router import Router
from result_store.result_store import Result_store
from utils.logging_utils import job_log_file
from openai_facade import OpenAIHTTPError, openai_error_response, v1

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("FASTAPI: LLM Gateway starting up.")
    yield
    logging.info("FASTAPI: LLM Gateway shutting down.")


app = FastAPI(lifespan=lifespan)
app.include_router(v1)


@app.exception_handler(OpenAIHTTPError)
def openai_http_error_handler(_: Request, error: OpenAIHTTPError) -> JSONResponse:
    logging.warning(
        f"FASTAPI: OpenAI facade error ({error.status_code}): {error.message} (code={error.code}, param={error.param})"
    )
    return openai_error_response(error)


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request: Request, error: RequestValidationError):
    """Give only the compatibility endpoint OpenAI-shaped validation errors."""
    logging.warning(f"FASTAPI: Validation error on {request.method} {request.url.path}: {error.errors()}")
    if request.url.path.startswith("/v1"):
        return openai_error_response(
            OpenAIHTTPError(
                400,
                "The request body is invalid.",
                param="request",
                code="invalid_request",
            )
        )
    return await request_validation_exception_handler(request, error)

@app.post("/api/async")
def process_async(data: Schema) -> dict[str, str]: # validation fails return an 422 error automatically by fastapi.

    job_id = str(uuid7()) #UUID 7 for time queryable id.

    with job_log_file(job_id):
        logging.info(f"FASTAPI:Request validity checked.")
        logging.info(f"FASTAPI: Async job id generated: {job_id}.")
        logging.info(f"FASTAPI: Received input: {data.model_dump(exclude_none=True)}.")

        # Insert record into DB before producing to queue
        Result_store().create_job(job_id, data.model_dump(exclude_none=True))

        try:
            Worker().produce_message({
                "job_id": job_id,
                "input":  data.model_dump(exclude_none=True),
                "status": "queued",
                "output" : None
            })

            logging.info(f"FASTAPI: Job queued successfully.")

        except HTTPException as e:
            logging.error(f"FASTAPI: Failed to queue async job {job_id}: {e.detail}")
            # Mark as failed if queueing fails.
            Result_store().update_job(job_id, status="failed", output=None) 
            raise e # raise since failure shouldn't be 200 OK, error code : 503 returned.
        except Exception as e:
            logging.error(f"FASTAPI: Unexpected error queueing async job {job_id}: {e}")
            Result_store().update_job(job_id, status="failed", output=None)
            raise HTTPException(status_code=500, detail={"job_id": job_id, "message": "Failed to queue job."})

    return {"job_id": job_id,
            "message": "Job queued successfully."}


@app.post("/api/sync")
def process_sync(data: Schema) -> Any:
    data_dict = data.model_dump(exclude_none=True)
    job_id = f"sync_{uuid7()}" #UUID 7 for time queryable id.


    with job_log_file(job_id):
        logging.info(f"FASTAPI:Request validity checked.")
        logging.info(f"FASTAPI: Sync job id generated: {job_id}.")
        logging.info(f"FASTAPI: Received input: {data_dict}.")

        if data.stream:
            def token_generator():
                chunk_count = 0
                try:
                    for chunk in Router().stream_route(data_dict):
                        chunk_count += 1
                        yield chunk
                    logging.info(f"FASTAPI: Streaming response completed for job {job_id} ({chunk_count} chunk(s)).")
                except Exception as e:
                    logging.error(f"FASTAPI: Stream failed mid-response: {e}")
                    raise

            logging.info("FASTAPI: Returning streaming response.")
            return StreamingResponse(token_generator(), media_type="text/plain")

        try:
            response = Router().route(data_dict)
        except Exception as e:
            # Check if this is the missing local model error
            if type(e).__name__ == "OllamaModelNotAvailableError":
                logging.error(f"FASTAPI: Model not found locally: {e}")
                raise HTTPException(status_code=404, detail={"job_id": job_id, "message": str(e)})

            logging.error(f"FASTAPI: Sync job failed: {e}")
            raise HTTPException(status_code=500, detail={"job_id": job_id, "message": "Job processing failed."})

        logging.info(f"FASTAPI: Job processed successfully.")
        logging.info(f"FASTAPI: Output generated: {response}.")

    return response


@app.get("/{job_id}")
def get_item(job_id: str) -> dict[str, Any]:
    logging.info(f"FASTAPI: Status check requested for job ID: {job_id}.")
    result = Result_store().check_status(job_id)
    if result is None:
        logging.warning(f"FASTAPI: Job ID {job_id} not found.")
        raise HTTPException(status_code=404, detail={"job_id": job_id, "message": "Job not found."})
    logging.info(f"FASTAPI: Job ID {job_id} status retrieved: {result.get('status')}.")
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
