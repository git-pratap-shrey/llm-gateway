#!/usr/bin/env bash
# tests/multimodal/test_image_curl.sh
#
# End-to-end test: downloads a sample image, base64-encodes it, exports it as
# BASE64_IMAGE, then fires the OpenAI-compatible multimodal request to the
# lgateway's /v1/chat/completions endpoint.
#
# Usage:
#   ./test_image_curl.sh [gateway_url] [model]
#
# Defaults:
#   gateway_url  → http://localhost:8000
#   model        → ollama_cloud/gemma4:cloud

set -euo pipefail

GATEWAY="${1:-http://localhost:8000}"
MODEL="${2:-ollama_cloud/gemma4:cloud}"
ENDPOINT="${GATEWAY}/v1/chat/completions"

# ── 1. Fetch a small random sample image ────────────────────────────────────
# Using the Picsum "seed" endpoint so results are reproducible.
SEED="${RANDOM}"
IMG_URL="https://picsum.photos/seed/${SEED}/400/300"
TMP_IMG="$(mktemp /tmp/test_img_XXXXXX.jpg)"

echo "→ Downloading sample image (seed=${SEED}) from ${IMG_URL} …"
curl -fsSL "${IMG_URL}" -o "${TMP_IMG}"
echo "  saved to ${TMP_IMG}"

# ── 2. Base64-encode and export ─────────────────────────────────────────────
export BASE64_IMAGE
BASE64_IMAGE="$(base64 -w 0 "${TMP_IMG}")"
echo "→ BASE64_IMAGE set (${#BASE64_IMAGE} chars)"

# ── 3. Fire the request ──────────────────────────────────────────────────────
echo ""
echo "→ Sending multimodal request to ${ENDPOINT} (model: ${MODEL}) …"
echo ""

curl "${ENDPOINT}" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ollama" \
  -d "{
    \"model\": \"${MODEL}\",
    \"messages\": [
      {
        \"role\": \"user\",
        \"content\": [
          {
            \"type\": \"text\",
            \"text\": \"Extract all text from this page. Return markdown text.\"
          },
          {
            \"type\": \"image_url\",
            \"image_url\": {
              \"url\": \"data:image/jpeg;base64,${BASE64_IMAGE}\"
            }
          }
        ]
      }
    ],
    \"temperature\": 0
  }" | python3 -m json.tool || true

# ── 4. Clean up ───────────────────────────────────────────────────────────────
rm -f "${TMP_IMG}"
echo ""
echo "Done."
