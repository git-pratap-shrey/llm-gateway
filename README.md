This is an message-queue based llm gateway, build on fastapi and rabbitmq. 

It allows developers to decouple their llm model into a microservice they can host on their server without worrying about rate limiting and all the providers and the different API protocols for different providers. All that is abstracted away.

In the event of a downtime or batch‑processing LLM requests, the gateway allows users to persist their requests and asynchronously complete them when available.

This also improves reusability among various projects people build, so that they don't have to repeat the same logic everywhere.

## OpenAI-compatible chat completions

The gateway also exposes a synchronous, OpenAI-compatible endpoint at
`POST /v1/chat/completions`. Prefix the model name with the target provider:
`ollama/<model>`, `gemini/<model>`, or `openrouter/<model>`.

```bash
curl http://localhost:8000/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "ollama/gemma4:cloud",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

It works with the standard OpenAI Python client; `api_key` is currently
accepted only for client compatibility and is not authenticated by the gateway.

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="x")
completion = client.chat.completions.create(
    model="ollama/gemma4:cloud",
    messages=[{"role": "user", "content": "Hello"}],
)
print(completion.choices[0].message.content)
```

Streaming, tools, multimodal message parts, and `n > 1` are not yet supported.
The original `/api/sync` and `/api/async` endpoints remain available unchanged.
