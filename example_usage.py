import requests

url = "http://localhost:8000/api/async"
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
res = requests.post(url, json=payload)
print(res.status_code, res.text)
