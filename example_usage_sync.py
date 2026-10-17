import logging
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

payload = {
    "provider": "ollama_cloud",
    "model": "gemma4:cloud",
    "messages": [
      {
        "role": "user",
        "content": "Hello there, this is obi wan"
      }
    ]
}


## sync endpoint:
logging.info(f"Sending sync request for model '{payload['model']}'...")
response = requests.post("http://localhost:8000/api/sync", json=payload)

if response.status_code == 200:
    logging.info(f"--- Sync Endpoint Success ({response.status_code}) ---: {response.text}")
else:
    logging.error(f"--- Sync Endpoint Error ({response.status_code}) ---: {response.text}")


# curl -X POST https://lm-gateway.git-pratap-shrey.online/api/sync \ 
#   -H "Content-Type: application/json" \
#   -d '{
#     "provider": "ollama",
#     "model": "gemma4:cloud",
#     "messages": [
#       {
#         "role": "user",
#         "content": "Hello, i am obi wan kenobi."
#       }
#     ]
#   }'