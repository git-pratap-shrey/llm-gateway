# LLM Gateway

A high-performance, message-queue-backed LLM gateway built on **FastAPI**, **RabbitMQ**, and **SQLite/SQLModel**.

It decouples LLM consumption into an isolated microservice that abstracts away provider-specific API protocols, manages rate limits via round-robin key pooling and worker pinning, provides automatic retry and fallback ladders across providers, and persists batch/async requests durably during traffic spikes or provider downtime.

---

## Key Features

- **Unified Schema & Providers:** Canonical interface for `ollama_cloud`, `gemini`, and `openrouter`.
- **OpenAI-Compatible Facade (`POST /v1/chat/completions`):** Drop-in replacement for OpenAI SDK clients; supports standard completions, Server-Sent Events (SSE) streaming, and multimodal vision inputs.
- **Durable Async Processing (`POST /api/async` & `GET /{job_id}`):** Persist-first queue architecture with UUIDv7 job tracking and pollable status (`queued` → `processing` → `completed` | `failed`).
- **Resilience & Automatic Fallbacks:** Bounded retries (up to 3× per provider) with automatic escalation across provider tiers (`ollama_cloud` → `openrouter` → `gemini`).
- **Rate-Limit & Key Pooling:** Round-robin API key rotation from environment variables, plus worker key pinning (`spawn_workers.py`) to bypass per-key concurrency bottlenecks.
- **Operational & Stuck-Job Tooling:** Pre-flight key validation (`check_keys.py`), connection timeout protection (`OLLAMA_CLOUD_TIMEOUT`), and stuck job recovery utilities (`rescue_jobs.py`, `republish_stuck.py`).

---

## Quickstart

### 1. Requirements & Setup

- Python ≥ 3.12 with [`uv`](https://docs.astral.sh/uv/)
- RabbitMQ running locally or in Docker (`localhost:5672`)
- Provider API keys set in `.env` (comma-separated for key pools):

```bash
# .env
OLLAMA_API_KEY="key1,key2"
GEMINI_API_KEY="key1"
OPENROUTER_API_KEY="key1"
RABBITMQ_HOST="localhost"
RESULT_DB_PATH="data/result_db.db"
LOG_DIR="logging"
```

### 2. Pre-Flight Key Health Check

Verify connectivity and quota across all keys in `.env`:

```bash
# Fast check (/models endpoint, <2s)
uv run python check_keys.py --fast

# Full completion check
uv run python check_keys.py

# Check a single provider
uv run python check_keys.py --provider ollama
```

### 3. Run the Services

```bash
# Terminal 1: Start FastAPI Gateway
uv run uvicorn main:app --reload --port 8000

# Terminal 2: Start a Background Queue Worker (for /api/async)
uv run python worker.py

# Alternatively: Spawn multiple pinned worker containers
uv run python spawn_workers.py -n 4
```

---

## API Usage

### 1. OpenAI-Compatible Chat Completions (`POST /v1/chat/completions`)

Compatible with the official OpenAI SDK and standard tools. Models are specified as `<provider>/<model>`:
- `ollama_cloud/gemma4:cloud`
- `gemini/gemini-2.0-flash`
- `openrouter/google/gemma-4-31b-it:free`

#### Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="not-needed")

# Standard completion
completion = client.chat.completions.create(
    model="ollama_cloud/gemma4:cloud",
    messages=[{"role": "user", "content": "Explain quantum computing in one sentence."}],
)
print(completion.choices[0].message.content)
```

#### Streaming (SSE)

```python
stream = client.chat.completions.create(
    model="gemini/gemini-2.0-flash",
    messages=[{"role": "user", "content": "Write a poem about distributed systems."}],
    stream=True,
)
for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
print()
```

#### Multimodal Vision (Text + Image)

Send base64-encoded images using standard OpenAI `image_url` parts:

```python
completion = client.chat.completions.create(
    model="gemini/gemini-2.0-flash",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What does this image show?"},
                {
                    "type": "image_url",
                    "image_url": {"url": "data:image/jpeg;base64,<BASE64_DATA>"},
                },
            ],
        }
    ],
)
print(completion.choices[0].message.content)
```

*(See [tests/multimodal/README.md](file:///home/anon/PROJECTS/llm_gateway/tests/multimodal/README.md) for shell and Python E2E test scripts).*

#### curl Example

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ollama_cloud/gemma4:cloud",
    "messages": [{"role": "user", "content": "Hello!"}],
    "temperature": 0.7
  }'
```

---

### 2. Synchronous Gateway API (`POST /api/sync`)

Synchronous endpoint taking the gateway's native `Schema`:

```bash
curl http://localhost:8000/api/sync \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "gemini",
    "model": "gemini-2.0-flash",
    "messages": [{"role": "user", "content": "Hello!"}],
    "parameters": {"temperature": 0.5, "max_tokens": 128},
    "stream": false
  }'
```

---

### 3. Asynchronous Queue API (`POST /api/async` & `GET /{job_id}`)

Fire-and-forget job submission persisted in SQLite and processed asynchronously via RabbitMQ:

```bash
# 1. Submit job
RESP=$(curl -sS -X POST http://localhost:8000/api/async \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama_cloud",
    "model": "gemma4:cloud",
    "messages": [{"role": "user", "content": "Summarize README.md"}],
    "parameters": {"temperature": 0.3}
  }')

JOB_ID=$(echo $RESP | python3 -c "import sys, json; print(json.load(sys.stdin)['job_id'])")
echo "Submitted Job: $JOB_ID"

# 2. Poll for result
curl http://localhost:8000/$JOB_ID
```

For complete specification, polling workflows, error tables, and client examples in Python and Node.js, see [ASYNC_API.md](file:///home/anon/PROJECTS/llm_gateway/ASYNC_API.md).

---

## Operational & Recovery Tooling

| Tool | Purpose | Example |
|---|---|---|
| [`check_keys.py`](file:///home/anon/PROJECTS/llm_gateway/check_keys.py) | Pre-flight key connectivity and quota validation | `uv run python check_keys.py --fast` |
| [`rescue_jobs.py`](file:///home/anon/PROJECTS/llm_gateway/rescue_jobs.py) | Unstick jobs stranded in `processing` state | `uv run python rescue_jobs.py --queued --older-than 300` |
| [`republish_stuck.py`](file:///home/anon/PROJECTS/llm_gateway/republish_stuck.py) | Re-publishes unhandled stuck jobs back to RabbitMQ | `uv run python republish_stuck.py` |
| [`spawn_workers.py`](file:///home/anon/PROJECTS/llm_gateway/spawn_workers.py) | Multi-worker Docker runner with key pinning | `uv run python spawn_workers.py -n 4` |

---

## Feature Matrix

| Feature | Status | Notes |
|---|---|---|
| **Chat Completions** | Supported | Canonical sync, async, and `/v1` endpoints |
| **Streaming (SSE)** | Supported | Available on `/v1/chat/completions` and `/api/sync` (`stream=True`) |
| **Multimodal Vision** | Supported | Image + text parts supported across providers via `image_url` |
| **Provider Fallback** | Supported | Automatic escalation (`ollama_cloud` → `openrouter` → `gemini`) |
| **Key Pooling & Pinning** | Supported | Round-robin key rotation and container key pinning |
| **Stuck Job Recovery** | Supported | Auto-ack safety nets, socket timeouts (120s), and `rescue_jobs.py` |
| **Tools / Tool Choice** | Not supported | Rejection with `400 invalid_request_error` |
| **JSON Mode / `response_format`** | Not supported | Rejection with `400 invalid_request_error` |
| **Multiple completions (`n > 1`)** | Not supported | Rejection with `400 invalid_request_error` |
| **Gateway Authentication** | Not supported | `api_key` accepted for client compatibility only |
