# Multimodal Test Suite

End-to-end tests for the gateway's multimodal (image + text) support via the
`/v1/chat/completions` OpenAI-compatible endpoint.

## Scripts

| Script | What it does |
|--------|-------------|
| `test_image_curl.sh` | Downloads a random sample image, base64-encodes it into `$BASE64_IMAGE`, then fires the OpenAI-compatible curl request to the gateway |
| `test_image_python.py` | Same flow in pure Python using `httpx` — useful for CI or when `curl` isn't available |

## Quick start

```bash
# 1. Start the gateway
uv run uvicorn main:app --reload

# 2. In another terminal, run the shell test
cd tests/multimodal
chmod +x test_image_curl.sh
./test_image_curl.sh

# 3. Or run the Python test (auto-installs httpx if needed)
python test_image_python.py
```

## Model name convention

The gateway's `/v1/chat/completions` endpoint uses the `<provider>/<model>` convention:

```
ollama_cloud/gemma4:cloud
gemini/gemini-2.0-flash
openrouter/google/gemma-4-31b-it:free
```

The test defaults to `ollama_cloud/gemma4:cloud`, matching the curl example in the project readme.
