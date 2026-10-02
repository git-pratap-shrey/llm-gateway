import logging
import requests

payload = {
    "provider": "ollama",
    "model": "gemma4:cloud",
    "messages": [
      {
        "role": "user",
        "content": "Hello there, this is obi wan"
      }
    ]
}


## sync endpoint:

response = requests.post("http://localhost:8000/api/sync", json=payload)

logging.info("--- Sync Endpoint ---", response.text)


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