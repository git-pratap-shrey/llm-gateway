import uuid

from fastapi import FastAPI

from validation import Schema
from worker import Worker
from router import router
from result_store import check_status
    
app = FastAPI()


@app.post("/api/async")
async def process_async(data: Schema): # validation fails return an 422 error automatically by fastapi.

    job_id = str(uuid.uuid7())

    worker = Worker()
    worker.produce_message({
        "job_id": job_id,
        "data":  data.model_dump(),
        "status": "queued"
    })

    return {"job_id": job_id,
            "message": "Job queued successfully."}



@app.post("/api/sync")
async def process_sync(data: Schema):
    data_dict = data.model_dump()

    response = router().route(data_dict)

    return response



@app.get("/{job_id}")
def get_item(job_id: str):
    return check_status(job_id)


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