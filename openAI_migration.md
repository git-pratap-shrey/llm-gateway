# Plan: OpenAI-compatible facade over the existing gateway

## Aim

Accept OpenAI Chat Completions requests on `POST /v1/chat/completions`, translate them into the existing `Schema`, call the existing `Router`, and wrap the result in an OpenAI-shaped response. **Nothing behind the facade changes.**

Untouched: `Schema` / `validation.py`, `Router`, provider adapters, `/api/sync`, `/api/async`, `GET /{job_id}`, worker, consumer, producer, result store.

Out of scope for now (later, one at a time): auth, retries/fallback, key rotation, async via OpenAI shape, streaming, tools/multimodal, parameter pass-through in adapters, generic OpenAI-SDK adapter, logging and queue fixes.

```
OpenAI client ──► POST /v1/chat/completions ──► [facade: validate + translate]
                                                      │
                                                      ▼
                                      Schema ──► Router ──► adapters (unchanged)
                                                      │
                                      [facade: wrap str → completion JSON]
```

## Files

- **New: `openai_facade.py`**: the `APIRouter(prefix="/v1")`, the request model, translation, the response builder, and the error class and handlers.
- **Edit: `main.py`**: `app.include_router(v1)` and register the exception handlers (2–3 lines).
- **New: `tests/pytest/test_openai_facade.py`**.

## Request

Permissive Pydantic model with `extra="allow"`:

| Field | Handling |
|---|---|
| `model` (required) | `"provider/model_name"`; split on the **first** slash |
| `messages` (required, non-empty) | Roles allowed: `system`, `developer`, `user`, `assistant`. Content must be a string, or a list of `{"type": "text"}` parts, which are joined into one string. Any other part type (image, audio) → 400. Roles `tool`, `function` and `model` → 400 |
| `temperature`, `top_p`, `frequency_penalty`, `presence_penalty` | Copied into `Parameter` |
| `max_tokens` / `max_completion_tokens` | Either maps to `max_tokens` (`max_completion_tokens` wins if both are present) |
| `stream: true` | 400 `unsupported_feature` |
| `tools`, `tool_choice`, `functions`, `response_format`, `n` > 1 | 400 `unsupported_feature` |
| Any other field (`user`, `stop`, `seed`, `stream_options`, ...) | Ignored. Names are listed in the `X-Gateway-Warnings` response header |

Model validation (400, code `invalid_model`, param `model`): no slash, empty provider, empty model name, or provider not supported. Derive the allowed providers from `Schema`'s `provider` Literal (so there's no second list to drift), and don't fall through to a default.

Range checks (`temperature` 0–2 and so on) come for free from `Parameter`. A `ValidationError` from `Schema(...)` becomes a 400.

## Translation

One pure function, `to_internal(req) -> Schema`, so it's easy to test:

```python
provider, _, model = req.model.partition("/")
Schema(
    provider=provider,
    model=model,
    messages=[{"role": m.role, "content": flatten(m.content)} for m in req.messages],
    parameters={...flat options..., "max_tokens": req.max_completion_tokens or req.max_tokens},
)
```

Then call `Router().route(schema.model_dump())` inside the handler (a regular `def`, so it runs in the threadpool as `/api/sync` does today).

## Response

```json
{
  "id": "chatcmpl-<uuid7>",
  "object": "chat.completion",
  "created": 1759500000,
  "model": "ollama/gemma4:cloud",
  "choices": [{"index": 0,
               "message": {"role": "assistant", "content": "<router output>"},
               "finish_reason": "stop"}],
  "usage": null
}
```

- `model` echoes the caller's prefixed value.
- `finish_reason` is always `"stop"` and `usage` is `null` for now: adapters only return text.
- If `Router` returns `None` or an empty value (for example a blocked Gemini response), return a 502 `empty_response` instead of a completion with `null` content.

## Errors

Define `OpenAIHTTPError(status, message, type, param, code)` and a handler that returns:

```json
{"error": {"message": "...", "type": "invalid_request_error", "param": "model", "code": "invalid_model"}}
```

| Situation | Status | Code |
|---|---|---|
| Validation, unknown provider, unsupported feature | 400 | `invalid_request` / `invalid_model` / `unsupported_feature` |
| Router/adapter raised | 502 | `upstream_error` |
| Router/adapter raised with a detectable 429 | 429 | `rate_limit_exceeded` (optional: check for a status code on the exception, otherwise 502) |
| Empty result | 502 | `empty_response` |

- Convert FastAPI's `RequestValidationError` into the same body, but **only for paths starting with `/v1`**. Other paths keep the default handler so `/api/*` behaves as before.
- Messages must not include API keys, base URLs or raw upstream exception text. Log the details server-side instead.
- Logging: provider and model only, never the prompt or output.

## Known gaps (accepted for now)

These come from keeping the current internals. All are on the "later" list.

- **Parameters are accepted but have no effect**, because the adapters ignore `Parameter`. `X-Gateway-Warnings` reflects only fields the facade itself dropped, so don't rely on it for upstream behavior until pass-through exists.
- **Multi-turn and system prompts on Gemini may fail**, because the Gemini adapter doesn't map `assistant` and `system` roles. This is an existing bug the facade will expose.
- **`usage` is null and `finish_reason` is fixed.**
- **Coarse error mapping**: nearly everything from the adapters becomes 502.
- **Two schemas** (the edge model and `Schema`) to keep in step. When tools or multimodal arrive, this is where to switch to OpenAI as the canonical schema.
- **`stream: true` is rejected.** Some chat UIs send it by default; a single-chunk SSE reply is a possible stopgap if that bites.

## Tests

Facade unit tests with `openai_facade.Router` patched (no network, no keys):

- Model parsing: first slash only, nested names, missing prefix or suffix, unknown provider.
- Translation: flat options land in `parameters`, `max_completion_tokens` alias, list-of-text content flattened, image part rejected, bad role rejected.
- Rejections: `stream: true`, `tools`, `response_format`, `n=2`.
- Unknown field is ignored and listed in `X-Gateway-Warnings`.
- Response shape: ids, `object`, prefixed `model`, `choices[0].message.content`, `usage` is null.
- Errors: OpenAI-shaped bodies; router exception → 502; empty result → 502; 422 handling applies on `/v1` only, `/api/*` unchanged.

Contract test (recommended, one test): `uv add --dev openai`, then call the app with a real `OpenAI` client via an `httpx` transport. It checks that a stock client can parse the response.

Then one manual smoke request per provider (`ollama`, `gemini`, `openrouter`) against real keys.

Run: `uv run pytest tests/pytest`

## Order of work

1. Request model, `to_internal`, and their unit tests.
2. Response builder and `OpenAIHTTPError` handlers.
3. The route, then `include_router` and handlers in `main.py`.
4. Route-level tests, then the contract test.
5. Smoke test per provider.
6. README: `curl` and `OpenAI` client examples using the `provider/model` form.

## Done when

`OpenAI(base_url="http://localhost:8000/v1", api_key="x").chat.completions.create(model="ollama/gemma4:cloud", messages=[...])` returns a parsed `ChatCompletion` whose text matches what `/api/sync` returns for the same input, and every `/api/*` route behaves exactly as before.

`/api/sync` stays for now; remove it later once nothing calls it.