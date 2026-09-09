# LLM Gateway — API Design

## 1. Overview

The gateway provides a **provider-agnostic API** for interacting with different LLM providers such as:

- Gemini
- xAI / Grok
- Ollama
- Other providers added later

The client interacts with one consistent API. The gateway is responsible for translating the canonical request into the format required by the selected provider.

The core philosophy is:

> **The gateway should make a best effort to fulfill the request and absorb provider-specific differences.**

---

## 2. Request Format

The canonical request format is:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user",
      "content": "Explain recursion."
    }
  ],
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "parameters": {
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 500
  }
}
```

### Fields

| Field | Required | Purpose |
|---|---:|---|
| `messages` | Yes | Conversation/input sent to the model |
| `provider` | Yes | Provider to use, e.g. `gemini`, `xai`, `ollama` |
| `model` | Yes | Model to use with the selected provider |
| `parameters` | No | Optional LLM generation parameters |

`parameters` is optional and can be omitted entirely:

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Explain recursion."
    }
  ],
  "provider": "ollama",
  "model": "llama3"
}
```

---

## 3. Provider-Agnostic Architecture

The gateway separates the public API from provider-specific implementations.

```text
                 Client
                   │
                   ▼
          ┌─────────────────┐
          │   LLM Gateway   │
          └────────┬────────┘
                   │
          Validate / Normalize
                   │
                   ▼
          ┌─────────────────┐
          │ Provider Router │
          └────────┬────────┘
                   │
       ┌───────────┼───────────┐
       ▼           ▼           ▼
    Gemini         xAI       Ollama
    Adapter      Adapter     Adapter
       │           │           │
       ▼           ▼           ▼
    Provider    Provider    Provider
      API          API         API
```

Each provider has an adapter responsible for translating the canonical gateway request into the provider's API format.

For example:

```text
Canonical parameter:
max_tokens

        ↓ Gemini Adapter

Provider parameter:
maxOutputTokens
```

The client should not need to know about these provider-specific differences.

---

## 4. Parameter Handling

The gateway exposes a common `parameters` object:

```json
{
  "parameters": {
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 500
  }
}
```

Different providers may support different parameters.

The gateway follows a **best-effort** approach.

For example:

```text
temperature        → supported       → apply
top_p              → supported       → apply
some_unknown_param → unsupported     → ignore
```

The gateway should still generate the response if possible.

### Important

Unsupported parameters should be **ignored and reported**, rather than silently ignored.

The caller does not necessarily need to know which parameter failed. The gateway only needs to indicate that something could not be applied.

---

## 5. Response Format

### Successful request

```json
{
  "code": 200,
  "warning": false,
  "message": {
    "role": "assistant",
    "content": "..."
  }
}
```

### Successful generation with a warning

```json
{
  "code": 200,
  "warning": true,
  "message": {
    "role": "assistant",
    "content": "..."
  }
}
```

The meaning is:

```text
code = 200
    → Gateway successfully generated a response

warning = false
    → Everything requested was handled

warning = true
    → Response was generated, but something requested
      could not be applied
```

The caller therefore does not need to understand provider-specific incompatibilities.

---

## 6. HTTP Status vs Application Code

The application-level `code` should be kept separate from the HTTP status.

For a successfully generated response:

```http
HTTP/1.1 200 OK
```

```json
{
  "code": 200,
  "warning": true,
  "message": {
    "role": "assistant",
    "content": "..."
  }
}
```

The HTTP request itself succeeded even if some optional configuration could not be applied.

Actual request or gateway failures can use appropriate HTTP status codes.

| HTTP Status | Example Meaning |
|---:|---|
| `400` | Malformed request |
| `401` | Authentication failure |
| `404` | Provider/model not found |
| `429` | Rate limit |
| `500` | Gateway failure |
| `502` | Provider failure |

`warning: true` is therefore reserved for **successful generation with degraded or partial configuration**.

---

## 7. Example: Best-Effort Processing

Client sends:

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Explain TCP."
    }
  ],
  "provider": "ollama",
  "model": "llama3",
  "parameters": {
    "temperature": 0.7,
    "top_p": 0.9,
    "some_provider_specific_parameter": 123
  }
}
```

The adapter determines:

```text
temperature                    → supported   → apply
top_p                          → supported   → apply
some_provider_specific_parameter → unsupported → ignore
```

The model is still called.

The gateway returns:

```json
{
  "code": 200,
  "warning": true,
  "message": {
    "role": "assistant",
    "content": "TCP is..."
  }
}
```

The caller gets the answer without needing to understand the specific provider incompatibility.

---

## 8. Core Contract

### Request

```text
REQUEST
├── messages        required
├── provider        required
├── model           required
└── parameters      optional
        └── LLM parameters
```

### Processing

```text
                  REQUEST
                     │
                     ▼
              Validate Request
                     │
                     ▼
              Provider Router
                     │
                     ▼
              Provider Adapter
                     │
                     ▼
             Translate Request
                     │
                     ▼
             Provider API
                     │
                     ▼
             Normalize Response
                     │
                     ▼
                  RESPONSE
```

### Response

```text
RESPONSE
├── code            application status code
├── warning         boolean
└── message
    ├── role
    └── content
```

---

## 9. Design Principles

The gateway should follow these principles:

1. **Provider agnostic**  
   Clients should interact with one stable API regardless of the underlying provider.

2. **Provider-specific logic stays in adapters**  
   Provider APIs and quirks should not leak into the public API.

3. **Best effort**  
   Unsupported optional parameters should not prevent generation when the request can otherwise be processed.

4. **Do not silently fail**  
   If something could not be applied, expose that through `warning: true`.

5. **Stable external contract**  
   Adding a new provider should not require changing the client's request format.

6. **Separate transport and application status**  
   HTTP status describes the HTTP/gateway operation; the response `code` and `warning` describe the application-level result.

---

## 10. Future Design Areas

The core contract above is the current foundation. Additional capabilities can be added while keeping the core structure stable.

Potential future areas:

- Streaming responses
- Multimodal messages / image inputs
- Tool/function calling
- Structured JSON output
- Authentication and API keys
- Provider/model capability discovery
- Normalized error responses
- Usage/token information
- Request IDs and tracing
- Retries and provider fallbacks
- Rate limiting
- Provider load balancing
