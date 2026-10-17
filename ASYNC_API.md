# Async Endpoint — Integration Guide

The gateway exposes a **fire-and-forget async endpoint** for decoupled LLM processing.  
Requests are persisted in a RabbitMQ queue and processed by one or more background workers.  
Results are stored in SQLite and polled by the caller at any time.

---

## Base URL

```
http://<gateway-host>:<port>
```

Default dev address: `http://localhost:8000`

---

## Workflow

```
1.  POST /api/async   →  {job_id}          (request accepted, queued)
2.  GET  /{job_id}    →  {status: "queued" | "processing" | "completed" | "failed"}
3.  Poll until status == "completed", then read the "response" field.
```

---

## Step 1 — Submit a job

### `POST /api/async`

**Request body** (`application/json`):

```jsonc
{
  "provider":  "ollama_cloud",          // "ollama_cloud" | "gemini" | "openrouter"
  "model":     "gemma4:cloud",          // model name as accepted by the provider
  "messages": [
    { "role": "user", "content": "Summarise this in three bullet points: ..." }
  ],
  "parameters": {                       // optional
    "temperature":        0.7,
    "top_p":              1.0,
    "top_k":              40,
    "max_tokens":         512,
    "frequency_penalty":  0.0,
    "presence_penalty":   0.0
  }
}
```

**Multimodal content** (vision models):

```jsonc
{
  "provider": "ollama_cloud",
  "model":    "gemma4:cloud",
  "messages": [
    {
      "role": "user",
      "content": [
        { "type": "text",      "text": "What does this image show?" },
        { "type": "image_url", "image_url": { "url": "data:image/jpeg;base64,<BASE64>" } }
      ]
    }
  ]
}
```

**Supported roles:** `user` | `assistant` | `system` | `developer` | `model`

---

#### Success response — `200 OK`

```json
{
  "job_id":  "018f1a2b-3c4d-7e5f-8a9b-0c1d2e3f4a5b",
  "message": "Job queued successfully."
}
```

#### Error responses

| Status | Cause |
|--------|-------|
| `422 Unprocessable Entity` | Request body failed schema validation (wrong provider, missing fields, etc.) |
| `503 Service Unavailable` | RabbitMQ is unreachable — the job was **not** persisted |

---

## Step 2 — Poll for results

### `GET /{job_id}`

```bash
curl http://localhost:8000/018f1a2b-3c4d-7e5f-8a9b-0c1d2e3f4a5b
```

#### Response — job in progress

```json
{
  "job_id":   "018f1a2b-3c4d-7e5f-8a9b-0c1d2e3f4a5b",
  "data":     "{...original input...}",
  "status":   "processing",
  "response": null
}
```

#### Response — job complete

```json
{
  "job_id":   "018f1a2b-3c4d-7e5f-8a9b-0c1d2e3f4a5b",
  "data":     "{...original input...}",
  "status":   "completed",
  "response": "Here are three bullet points: ..."
}
```

#### Response — job failed (all providers exhausted)

```json
{
  "job_id":   "018f1a2b-3c4d-7e5f-8a9b-0c1d2e3f4a5b",
  "data":     "{...original input...}",
  "status":   "failed",
  "response": "None"
}
```

#### Error responses

| Status | Cause |
|--------|-------|
| `404 Not Found` | No job exists for this `job_id` |

---

## Full examples

### curl

```bash
# Submit
JOB=$(curl -sS -X POST http://localhost:8000/api/async \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "ollama_cloud",
    "model":    "gemma4:cloud",
    "messages": [{"role": "user", "content": "Say hello in three languages."}],
    "parameters": {"temperature": 0.5, "max_tokens": 128}
  }' | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")

echo "Job ID: $JOB"

# Poll until done
while true; do
  RESP=$(curl -sS http://localhost:8000/$JOB)
  STATUS=$(echo $RESP | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  echo "Status: $STATUS"
  if [[ "$STATUS" == "completed" || "$STATUS" == "failed" ]]; then
    echo $RESP | python3 -m json.tool
    break
  fi
  sleep 2
done
```

---

### Python (`httpx`)

```python
import httpx
import time

GATEWAY = "http://localhost:8000"

# ── Submit ────────────────────────────────────────────────────────────────────
payload = {
    "provider": "ollama_cloud",
    "model":    "gemma4:cloud",
    "messages": [{"role": "user", "content": "Say hello in three languages."}],
    "parameters": {"temperature": 0.5, "max_tokens": 128},
}

with httpx.Client() as client:
    r = client.post(f"{GATEWAY}/api/async", json=payload)
    r.raise_for_status()
    job_id = r.json()["job_id"]

print(f"Job ID: {job_id}")

# ── Poll ──────────────────────────────────────────────────────────────────────
with httpx.Client() as client:
    while True:
        r = client.get(f"{GATEWAY}/{job_id}")
        r.raise_for_status()
        result = r.json()
        print(f"Status: {result['status']}")
        if result["status"] in ("completed", "failed"):
            break
        time.sleep(2)

print("Response:", result["response"])
```

---

### Python (`openai` client — sync facade, for comparison)

The `/v1/chat/completions` endpoint is **synchronous** and OpenAI-compatible.  
Use it when you want a drop-in OpenAI replacement without queue overhead.

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="x")

completion = client.chat.completions.create(
    model="ollama_cloud/gemma4:cloud",   # <provider>/<model>
    messages=[{"role": "user", "content": "Say hello in three languages."}],
)
print(completion.choices[0].message.content)
```

---

### JavaScript / Node (`fetch`)

```js
const GATEWAY = "http://localhost:8000";

// Submit
const submitRes = await fetch(`${GATEWAY}/api/async`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    provider: "ollama_cloud",
    model: "gemma4:cloud",
    messages: [{ role: "user", content: "Say hello in three languages." }],
    parameters: { temperature: 0.5, max_tokens: 128 },
  }),
});
const { job_id } = await submitRes.json();
console.log("Job ID:", job_id);

// Poll
const poll = async (jobId) => {
  while (true) {
    const res = await fetch(`${GATEWAY}/${jobId}`);
    const data = await res.json();
    console.log("Status:", data.status);
    if (data.status === "completed" || data.status === "failed") {
      return data;
    }
    await new Promise((r) => setTimeout(r, 2000));
  }
};

const result = await poll(job_id);
console.log("Response:", result.response);
```

---

## Job lifecycle

```
queued  ──▶  processing  ──▶  completed
                 │
                 └──▶  (retry same provider, up to 3×)
                              │
                              └──▶  (escalate to next provider)
                                         │
                                         └──▶  failed  (all providers exhausted)
```

**Automatic fallback order:**
1. `ollama_cloud / gemma4:cloud`
2. `openrouter  / google/gemma-4-31b-it:free`
3. `gemini      / gemma-4-31b-it`

The fallback ladder applies automatically — callers do not need to handle it.

---

## Provider reference

| Provider key | Models (examples) |
|---|---|
| `ollama_cloud` | `gemma4:cloud`, `llama3.3`, `qwen3:235b` |
| `gemini` | `gemini-2.0-flash`, `gemma-4-31b-it` |
| `openrouter` | `google/gemma-4-31b-it:free`, `meta-llama/llama-4-scout:free` |

---

## Schema validation rules

| Field | Constraint |
|---|---|
| `provider` | Must be one of the three literal values above |
| `messages` | Minimum 1 message |
| `parameters.temperature` | `0.0 – 2.0` |
| `parameters.top_p` | `0.0 – 1.0` |
| `parameters.top_k` | `≥ 1` |
| `parameters.max_tokens` | `≥ 1` |
| `parameters.frequency_penalty` | `-2.0 – 2.0` |
| `parameters.presence_penalty` | `-2.0 – 2.0` |
