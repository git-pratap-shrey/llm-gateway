import requests
import time

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

## async endpoint:
response = requests.post("http://localhost:8000/api/async", json=payload)


## start polling for the result:
if response.status_code == 200:
    job_id = response.json()["job_id"]
    poll_url = f"http://localhost:8000/{job_id}"
    
    while True:
        poll_res = requests.get(poll_url)
        poll_data = poll_res.json()
        if poll_data.get("status") == "completed":
            print("--- Async Endpoint ---")
            print(f"ID: {poll_data.get('job_id')}")
            print(f"Response: {poll_data.get('response')}")
            break
        time.sleep(1)
