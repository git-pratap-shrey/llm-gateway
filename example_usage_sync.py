import requests

payload = {
    "provider": "ollama",
    "model": "gemma4:cloud",
    "messages": [
      {
        "role": "user",
        "content": "Hello"
      }
    ]
}

## sync endpoint:

response = requests.post("http://localhost:8000/api/sync", json=payload)

print("--- Sync Endpoint ---", response.text)