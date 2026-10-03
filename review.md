# LLM Gateway — Codebase Review (3 Oct 2026)

Overall: the skeleton is clean (adapter → router → queue → store). Some earlier issues are fixed (e.g. the Ollama adapter now re-raises). There are still real bugs, some already exposed by the tests, and several design forks to settle before building the todo list.

---

## 1. Bugs and correctness issues (highest impact first)

1. **Parameters are validated, then dropped.** `Parameter` is parsed in `validation.py`, but none of the three adapters passes it to the provider. The `warning` contract from the design doc doesn't exist yet. Pydantic's default `extra="ignore"` means unknown params never reach the adapter, so they can't be reported as unsupported.
2. **Role handling breaks multi-turn and system prompts.** The schema allows `system`, `assistant`, `developer`, `model`, but Gemini `contents` only accepts `user`/`model`; system prompts belong in `config.system_instruction`. A Gemini request with a system or assistant message will likely fail. Role normalization belongs in each adapter.
3. **Failed jobs store the string `"None"`.** `update_job(..., output=None)` does `str(output)`. The failure reason is never stored either, so a polling client learns nothing.
4. **Concurrent log capture is wrong in the API process.** FastAPI runs sync endpoints in a threadpool; `job_log_file` attaches a handler to the process-global root logger, so job A's file captures lines from job B's thread. The consumer is single-threaded, so it's fine there. Fix: `contextvars` job ID plus a filter on each handler.
5. **Duplicate or lost messages.**
   - Pika's `BlockingConnection` can't service heartbeats while the callback blocks on a slow LLM call; the broker may drop the connection, the ack fails, and the job is redelivered and run twice.
   - No `basic_qos(prefetch_count=1)`, so multiple workers dispatch unevenly.
   - No publisher confirms, so a publish can be lost silently.
   - `Producer.send_message` leaks the connection if publish raises.
6. **Orphaned `queued` rows.** `main.py` only catches `HTTPException`; any other error from `Producer()` or publish leaves the row at `queued` forever.
7. **Router fallthrough.** The `else` branch sends any unknown provider to OpenRouter. `test_route_unknown_provider_returns_none` expects `None` and fails. The design doc lists xAI, which doesn't exist in code.
8. **Result store.**
   - `create_engine` + `create_all` run on every `Result_store()` call (several per request); use one module-level engine.
   - `data=str(input_data)` stores a Python repr, not JSON.
   - `check_status` is annotated `dict` but returns `None`.
9. **Ollama is cloud-only.** Host is hardcoded to `https://ollama.com`, so local Ollama can't be used. `os.environ['OLLAMA_API_KEY']` fails at request time, not startup.
10. **Gemini `reply.text` can be `None`** (e.g. blocked responses); it gets stored as `"None"` and the job is marked `completed`.

## 2. Security

- No auth anywhere, and the example files point at a public hostname. Anyone can spend your provider keys.
- `GET /{job_id}` returns prompts and responses to anyone holding the ID; UUIDv7 IDs are partly time-predictable.
- Minimum: API-key check plus per-key rate limits.
- Job log files record full prompts and outputs.

## 3. Broken or fragile tests

- `test_get_item_not_found` expects 200 and `None`, but the endpoint now raises 404.
- `test_process_async` mocks `Worker` and `uuid7` but not `Result_store`; it writes to the real SQLite file with a fixed ID, so the second run fails with `IntegrityError`.
- `GET /{job_id}` is a root catch-all that will collide with `/health`, `/v1/...`. Prefer `/api/jobs/{id}`.
- `example_usage_sync.py`: `logging.info("---", response.text)` has an argument with no placeholder and raises a logging formatting error.

## 4. Housekeeping

- `llm-gateway-design-decisions.md` still describes the fixed Ollama `None`-return bug and uses `input`/`output` column names where the code uses `data`/`response`.
- `jev_testing.py` and `typesafe-sdk` look unrelated to the gateway.
- `requests` is used but only arrives transitively.

---

## 5. Design forks to settle before building the todo list

### Fork 1 — Response contract vs. OpenAI-style `/v1` endpoint
The design doc uses `{code, warning, message}`; the todo list wants an OpenAI-compatible endpoint. These conflict.

| Option | Pros | Cons |
|---|---|---|
| Custom envelope | Expressive | No existing SDK can talk to it |
| OpenAI shape + extras (warnings in an extra field or `X-Gateway-Warnings` header) | Existing clients work unchanged; extras are ignored by OpenAI clients | Inherit its quirks |

Decide this first: multimodal, tool calling and streaming all follow from it.

### Fork 2 — Queue topology
| Option | Pros | Cons |
|---|---|---|
| Single `tasks` queue (current) | Simple | A slow or rate-limited provider blocks the rest (head-of-line blocking) |
| Queue per provider (topic exchange) | Failure isolation; per-provider concurrency tuning | More setup and more consumers |

A fallback is just a re-publish to another routing key, so this interacts with Fork 3.

### Fork 3 — Where retry and fallback live
| Option | Pros | Cons |
|---|---|---|
| In consumer/router code | Easy to write and test | Holds a worker slot during backoff; worsens the heartbeat problem |
| Broker-level (DLX + TTL delay queues) | No worker held; survives crashes | Harder to reason about and debug |

Middle path: in-process retries for fast transient errors (429, 5xx), DLX for longer delays. Either way, define a shared retryable-vs-permanent error taxonomy in the adapters.

### Fork 4 — The DB + queue dual write
Insert-then-publish is sensible but not atomic.

| Option | Pros | Cons |
|---|---|---|
| Keep RabbitMQ + sweeper requeueing rows stuck in `queued`/`processing` | Cheap | At-least-once, so workers must be idempotent |
| Transactional outbox | Correct | Adds a relay process |
| Postgres queue (`FOR UPDATE SKIP LOCKED`) | Row and job in one transaction; one less moving part; retries/status/visibility for free | You build your own queue; lose RabbitMQ routing; changes the "message-queue based" identity |

### Fork 5 — Async-first vs. blocking pika
| Option | Pros | Cons |
|---|---|---|
| Keep pika | Fine at this scale (reuse one connection/channel per process) | Not async-first; no streaming |
| `aio-pika` + async provider SDKs | Fits the event loop; enables streaming | Rewrite of worker and adapters |

### Fork 6 — Conversation memory
| Option | Pros | Cons |
|---|---|---|
| Stateless (client sends history) | Simple, predictable, cheap; the OpenAI model | Client manages history |
| Server-side threads | Convenient | Storage, truncation/summarization policy, privacy |

Lean stateless first; add threads later as a separate resource.

### Fork 7 — Key rotation and load balancing
LiteLLM's proxy already does key pools, fallbacks and an OpenAI-compatible API. What's distinctive here is durable queued execution; emphasize that in the presentation. Build a minimal in-process key pool with cooldown on 429; don't chase full load balancing yet.

---

## 6. Provider SDK notes

**Caveat:** these notes come from reading the adapter code plus my own knowledge. They have **not** been verified against current (Oct 2026) docs. Treat them as a checklist to verify, not as confirmed findings.

### Gemini (`google-genai`)
- Roles are `user` / `model`. `assistant` and `system` in `contents` are likely rejected.
- System prompt goes in `GenerateContentConfig(system_instruction=...)`.
- Generation params go in `GenerateContentConfig`: `temperature`, `top_p`, `top_k`, `max_output_tokens` (not `max_tokens`), plus `frequency_penalty` / `presence_penalty` on supported models.
- `automatic_function_calling` disable is harmless but unnecessary when no tools are passed.
- A new `genai.Client()` is created per request; reuse one per process. An async client exists at `client.aio`.
- `response.text` may be `None` (blocked or empty candidates); check `finish_reason` / prompt feedback.
- Only `errors.APIError` is caught; no timeout configured (`http_options`).
- `list_models` swallows errors and returns `[]`, while `chat` raises: inconsistent.

### Ollama (`ollama`)
- `Client(host=..., headers={"Authorization": "Bearer ..."})` is the right pattern for Ollama Cloud.
- Parameters go in `options={...}`: `temperature`, `top_p`, `top_k`, `num_predict` (not `max_tokens`), and penalties.
- Roles: `system` / `user` / `assistant` (and `tool`); `model` / `developer` are not valid.
- Make host configurable (local vs cloud); read the API key at startup, not per request.
- `AsyncClient` exists for the async-first path.
- Responses support both attribute and subscript access, so `reply["message"]["content"]` works.

### OpenRouter (`openrouter` SDK)
- `client.chat.send(model=..., messages=...)` matches the SDK's chat entry point as far as I know. Verify parameter names for temperature / top_p / max tokens against the current SDK.
- `reply.choices[0].message.content` can be `None` (e.g. tool calls or refusals); guard it.
- OpenRouter has its own provider routing and model fallback options, which may overlap with your Fork 3 fallback logic. Check the docs before building your own.
- `model` and `developer` roles are not valid here either; normalize in the adapter.
- A bare `except Exception` is used here, whereas the other adapters catch SDK-specific errors. Catch the SDK's error types so you can classify retryable errors.

### Cross-cutting
- Each adapter should expose the same contract: normalize roles, map canonical params to provider params, return `(text, usage, finish_reason, warnings)`, and raise typed errors (`RateLimited`, `AuthError`, `BadRequest`, `ProviderDown`).
- Reuse one client per process in each adapter instead of constructing one per call.

---

## 7. Suggested order of work

1. Fix the quick bugs (items 3, 6, 7, 8, role mapping, test failures).
2. Add auth.
3. Pick the response contract (Fork 1).
4. Pass parameters through adapters and return warnings.
5. Then retry and fallback, with the queue topology decided.