# LLM Gateway — Design Decisions

Two decisions from the logging/persistence design discussion, kept here for reference during implementation.

---

## 1. Per-job-ID logging files

**Decision:** One log file per job, named by `job_id`, stored in a `logging/` folder — not a single shared log file, and not a hand-rolled write-per-event helper.

**Why:**
- A single shared log file (`logs/gateway.log`) requires filtering by `job_id` to debug one job, and becomes unsafe across multiple processes later (concurrent writers/rotation corrupts the file). Per-job files sidestep this: two different job IDs never write to the same file, regardless of how many worker processes exist — so no rework is needed when concurrency is added later.
- A hand-rolled `log_event()` helper that writes JSON lines directly works, but throws away the existing `logging.info(...)` / `logging.error(...)` calls already spread across the codebase — every call site would need to change.
- The chosen approach instead attaches a **handler** (not a new named logger) to the **root logger** for the duration of a job. `logging.getLogger(name)` is never garbage collected for the life of the process, so creating a new named logger per job leaks memory; a handler you explicitly `removeHandler()` does not. Because it hooks the root logger, every existing `logging.info(...)`/`logging.error(...)` call anywhere in the codebase (router, adapters, worker) is captured automatically for that job with zero changes to those call sites.

**Implementation:**

```python
import logging
import os
from contextlib import contextmanager

LOG_DIR = "logging"

@contextmanager
def job_log_file(job_id: str):
    os.makedirs(LOG_DIR, exist_ok=True)
    handler = logging.FileHandler(f"{LOG_DIR}/{job_id}.log")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()          # root, not a named logger
    root.addHandler(handler)
    try:
        yield
    finally:
        root.removeHandler(handler)
        handler.close()
```

**Where it wraps** — `message_queue/consumer.py`, `Consumer.callback`:

```python
def callback(self, ch, method, properties, body):
    payload = json.loads(body.decode())
    job_id = payload["job_id"]

    with job_log_file(job_id):
        logging.info(f"Received job ID {job_id} for processing.")
        payload["output"] = Router().route(payload["input"])
        payload["status"] = "completed"
        logging.info(f"Processed job ID {job_id}")

    Result_store().add_to_database(payload)
    ch.basic_ack(delivery_tag=method.delivery_tag)
```

Same pattern applies to `main.py`'s `process_async` (wrap from job-ID generation through `produce_message`, so the enqueue log line is captured too). `process_sync` doesn't have a persisted `job_id` today, so it either needs one generated just for the log filename, or can be skipped since the sync response is already returned directly to the caller.

**Not yet decided / follow-ups:** whether to also wrap `process_sync`; whether to add rotation or cleanup of old job log files once the folder grows large (not urgent).

---

## 2. Insert the DB row at enqueue time, not at completion

**Decision:** `Result_store` creates a row with `status="queued"`, `output=None` when the job is enqueued (in `main.py`, before/around producing to RabbitMQ) — not only after the consumer finishes processing it.

**Why:**
- Today, no row exists until the consumer finishes. Polling `GET /{job_id}` while a job is `queued` or `processing` returns "not found" — indistinguishable from a typo'd or nonexistent `job_id`. This breaks the core purpose of the async polling endpoint.
- If the worker crashes mid-processing (provider hangs, process killed, etc.), there is no database row at all for that job — no way to even discover it existed and got stuck. Inserting at enqueue time means a `queued`/`processing` row stuck for too long is a visible, queryable signal of failure, instead of total silence.

**Implementation:**

`Result_store` needs two distinct methods instead of one reused insert — since `job_id` is the primary key, calling the same insert method twice (once at enqueue, once at completion) will raise an `IntegrityError`:

```python
def create_job(self, job_id: str, input_data: dict) -> None:
    with Session(self.engine) as session:
        session.add(Result(job_id=job_id, status="queued", output=None, input=str(input_data)))
        session.commit()

def update_job(self, job_id: str, status: str, output: Any) -> None:
    with Session(self.engine) as session:
        row = session.get(Result, job_id)
        row.status = status
        row.output = str(output)
        session.commit()
```

**Call sites:**

- `main.py`, `process_async` — create the row *before* producing to the queue:

```python
job_id = str(uuid7())
Result_store().create_job(job_id, data.model_dump())   # status="queued", output=None
Worker().produce_message({"job_id": job_id, "input": data.model_dump()})
```

- `message_queue/consumer.py`, `Consumer.callback` — call `update_job(...)` instead of the old `add_to_database(...)` once processing finishes.

**Ordering matters:** insert into the DB *before* producing to the queue, not after.
- If DB-insert-first and the *queue* produce fails (`worker.py` already raises a 503 for `AMQPConnectionError`), you get a harmless orphaned `queued` row that's never processed — annoying but visible, not silently broken. Optional cleanup:

```python
try:
    Worker().produce_message({...})
except HTTPException:
    Result_store().update_job(job_id, status="failed", output=None)
    raise
```

- If queue-produce-first and the DB insert then fails, a worker could pick up a message with no row to update, and `update_job`'s `session.get(...)` would return `None` and crash.

**Optional addition:** have the consumer call `update_job(job_id, status="processing", output=None)` when it picks the message off the queue, before calling `Router().route()` — gives clients a `processing` state distinct from `queued` for slow provider calls. Not required to start; a nice-to-have.

**Not yet decided / follow-ups:** whether to implement the "mark failed if queue-produce fails" cleanup step; whether to add the intermediate `processing` status update.

---

## Related, still open

- Retry policy per provider (what counts as retryable — rate limits vs. auth errors vs. validation errors) and where the central retry wrapper lives (`Router.route()` vs. a decorator) — not yet settled.
- Planned move from SQLite to PostgreSQL once concurrent workers are introduced (not urgent while running single-process).
- Existing bug: `providers/ollama_client.py`'s `chat()` catches `ResponseError`, logs it, and implicitly returns `None` — `router.py` will then throw `AttributeError` on `reply["message"]["content"]`. Worth fixing before retry logic is added, since retries need adapters to raise, not swallow-and-return-None.
