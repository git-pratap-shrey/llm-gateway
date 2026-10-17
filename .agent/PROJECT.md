# LLM Gateway — Agent Context

> This file is the single source of truth for any AI agent working on this project.  
> Read this before touching anything. Do not look up individual files unless you need  
> implementation detail not covered here.

---

## What the project is

A **message-queue-backed LLM gateway** built on FastAPI + RabbitMQ.  
It decouples LLM calls into a microservice so callers don't have to manage:
- provider-specific API protocols
- API key rotation / pooling
- rate-limit retries and automatic provider fallback
- async request persistence and polling

---

## Directory layout

```
llm_gateway/
├── main.py                  # FastAPI app — all HTTP endpoints
├── router.py                # Routes requests to provider Serve_* classes
├── validation.py            # Pydantic Schema / Message / Parameter models
├── openai_facade.py         # OpenAI-compatible /v1/chat/completions endpoint
├── worker.py                # Worker entry-point (produce + consume)
├── spawn_workers.py         # Docker-based multi-worker manager (CLI)
├── check_keys.py            # Pre-flight API key health and status check CLI
├── rescue_jobs.py           # Unstick jobs stranded in 'processing' state (CLI)
├── republish_stuck.py       # Re-publishes stuck jobs directly to RabbitMQ (script)
├── config.py                # Provider URLs, timeout (120s), env var names, fallback order
├── message_queue/
│   ├── producer.py          # Pika publisher → "tasks" queue (durable)
│   ├── consumer.py          # Pika consumer with retry + fallback logic
│   └── fallback.py          # Provider escalation ladder (PRIORITY_1→2→3)
├── providers/
│   ├── ollama_cloud_client.py  # openai.OpenAI → https://ollama.com/v1
│   ├── gemini_client.py        # openai.OpenAI → Gemini OpenAI-compat endpoint
│   ├── openrouter_client.py    # openai.OpenAI → OpenRouter
│   └── key_pool.py             # Round-robin key rotation from a comma-sep list
├── result_store/
│   ├── result_store.py      # SQLite CRUD via SQLModel (create/update/check)
│   └── results_db.py        # SQLModel table: Result(job_id, data, status, response)
├── utils/logging_utils.py   # job_log_file() context manager (per-job log files)
├── tests/
│   ├── pytest/              # Unit tests (pytest)
│   └── multimodal/          # E2E multimodal image tests (curl + Python)
└── .env                     # API keys (NOT committed in prod)
```

---

## Core models (`validation.py`)

```python
class Message(BaseModel):
    role: Literal["system","user","assistant","developer","model"]
    content: str | list[dict]   # list[dict] = multimodal parts (text / image_url)

class Parameter(BaseModel):
    temperature, top_p, top_k, max_tokens, frequency_penalty, presence_penalty

class Schema(BaseModel):
    provider:   Literal["gemini", "openrouter", "ollama_cloud"]
    model:      str
    messages:   list[Message]   # min 1
    parameters: Parameter | None = None
    stream:     bool = False
```

`Message.content` accepts **either a plain string or a list of OpenAI content-part dicts** (added for multimodal support). The provider clients forward `messages` verbatim to the OpenAI SDK, so vision/image payloads flow through unchanged.

---

## HTTP endpoints (`main.py` + `openai_facade.py`)

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/sync` | Synchronous call — blocks until the provider responds. Supports streaming via `"stream": true`. |
| `POST` | `/api/async` | Async — enqueues the job in RabbitMQ, returns `{job_id, message}` immediately. |
| `GET`  | `/{job_id}` | Poll async job status: `queued → processing → completed / failed`. |
| `POST` | `/v1/chat/completions` | **OpenAI-compatible facade.** Model name must be `<provider>/<model>`. Supports multimodal content parts. |

### `/v1/chat/completions` model naming
```
ollama_cloud/gemma4:cloud
gemini/gemini-2.0-flash
openrouter/google/gemma-4-31b-it:free
```

### Multimodal support (image_url)
`flatten_content()` in `openai_facade.py`:
- **Text-only list** → collapsed into a single string (backward-compat)
- **List with any `image_url` part** → passed through as-is to the OpenAI SDK
- Plain string → unchanged

---

## Providers (`router.py` + `providers/`)

All three clients wrap `openai.OpenAI` pointed at different base URLs.

| Provider key | Base URL | Client class |
|---|---|---|
| `ollama_cloud` | `https://ollama.com/v1` | `OllamaCloudClient` |
| `gemini` | `https://generativelanguage.googleapis.com/v1beta/openai/` | `GeminiClient` |
| `openrouter` | `https://openrouter.ai/api/v1` | `OpenrouterClient` |

**`KeyPool`** (`providers/key_pool.py`): round-robin over comma-separated keys from env var.  
`Router.route()` and `Router.stream_route()` dispatch by `input["provider"]`.

---

## Async queue internals

```
POST /api/async
    → create DB row (status=queued)
    → Producer.send_message() → RabbitMQ "tasks" queue (durable, persistent)
    ← {job_id}

Worker (consumer container)
    → Consumer.start_consuming()
    → callback():
        ├── Outer try:
        │   ├── with job_log_file(job_id):
        │   │   ├── DB update: processing
        │   │   ├── Router().route(input) (with OLLAMA_CLOUD_TIMEOUT=120s)
        │   │   ├── success → DB update: completed + output
        │   │   └── failure:
        │   │       ├── retry_count < MAX_RETRIES → requeue same provider (retry_count++)
        │   │       ├── escalate_provider() → requeue next provider (fallback_index++)
        │   │       └── all exhausted → DB update: failed
        │   └── outer exception: mark failed in DB (prevents unhandled stuck 'processing')
        └── finally:
            └── ch.basic_ack() — always acknowledges delivery tag to protect broker health

GET /{job_id}
    → Result_store().check_status() → SQLite lookup
```

### Fallback ladder (`config.py` + `fallback.py`)
```
PRIORITY_1: ollama_cloud / gemma4:cloud
PRIORITY_2: openrouter  / google/gemma-4-31b-it:free
PRIORITY_3: gemini      / gemma-4-31b-it
MAX_RETRIES = 3
```
Within each tier, the job is retried up to `MAX_RETRIES` times before escalating to the next provider. Original provider is skipped in the fallback list.
`config.OLLAMA_CLOUD_TIMEOUT = 120.0` prevents consumer workers from hanging indefinitely on network stalls.

---

## Result store (`result_store/`)

SQLite via SQLModel. DB path from `RESULT_DB_PATH` env var (default: `result_db.db`).

**`Result` table columns:** `job_id (PK) | data (str) | status (str) | response (str|None)`

Statuses: `queued → processing → completed | failed`

---

## Environment variables

| Variable | Used by | Notes |
|---|---|---|
| `OLLAMA_API_KEY` | `router.py` | Comma-separated → KeyPool (one key pinned per worker container) |
| `GEMINI_API_KEY` | `router.py` | Comma-separated → KeyPool |
| `OPENROUTER_API_KEY` | `router.py` | Comma-separated → KeyPool |
| `RABBITMQ_HOST` | producer + consumer | Default: `localhost` |
| `RESULT_DB_PATH` | result_store | Default: `result_db.db` |

---

## Running the stack

```bash
# Pre-flight API key health check
uv run python check_keys.py --fast          # Quick connectivity/auth check (<2s)
uv run python check_keys.py                 # Full completion check across all keys

# Gateway (dev)
uv run uvicorn main:app --reload

# Single local worker (no Docker)
uv run python worker.py

# Docker multi-worker (reads .env for OLLAMA_API_KEY pool)
uv run python spawn_workers.py -n 4
# Flags: --no-restart, --check-interval, --status-interval, -f <compose-file>
# PIN=0 uv run python spawn_workers.py -n 4   # unpin keys (all workers share all keys)

# Stuck job recovery
uv run python rescue_jobs.py --queued       # Reset stuck 'processing' jobs to 'queued'
uv run python rescue_jobs.py --failed       # Mark stuck 'processing' jobs as 'failed'
uv run python rescue_jobs.py --queued --older-than 300 --dry-run
```

---

## Tests

```bash
# Unit tests
uv run pytest tests/pytest/

# Multimodal E2E (gateway must be running)
./tests/multimodal/test_image_curl.sh [gateway_url] [model]
python tests/multimodal/test_image_python.py [gateway_url] [model]
```

---

## Key design decisions to remember

1. **Provider clients don't need to change for multimodal** — they pass `messages` straight to the OpenAI SDK which handles vision natively.
2. **`/v1/chat/completions` is synchronous** — it calls `Router().route()` directly without RabbitMQ. Async path is `/api/async`.
3. **Worker key pinning** — `spawn_workers.py` assigns one Ollama API key per container (`PIN=1` default) by overriding the env var at `docker run` time, enabling per-key concurrency tracking.
4. **Stuck-job defense-in-depth** — `OLLAMA_CLOUD_TIMEOUT` limits remote calls to 120s; consumer callback wraps work in outer `try...finally` with `ch.basic_ack` to ensure messages are not left in limbo; `rescue_jobs.py` provides administrative recovery for stranded DB rows.
5. **`Schema.provider`** is a Literal — adding a new provider requires updating `validation.py`, `router.py`, `config.py`, and creating a new client in `providers/`.
6. **`uuid7`** is used for all job IDs (time-sortable UUIDs).
7. **`exclude_none=True` on serialization** — `data.model_dump(exclude_none=True)` ensures cleaner payloads in DB and queues without sparse `None` fields.
