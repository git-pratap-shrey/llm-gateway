import logging
import requests
import time

payload = {
    "provider": "ollama_cloud",
    "model": "gemma4:cloud",
    "messages": [
      {
        "role": "user",
        "content": "Hello"
      }
    ]
}

## async endpoint:
response = requests.post("https://lm-gateway.git-pratap-shrey.online/api/async", json=payload)

job_id = response.json()["job_id"]
print(f"Async request initiated. Job ID: {job_id}")

## start polling for the result:
if response.status_code == 200:
    poll_url = f"https://lm-gateway.git-pratap-shrey.online/api/async/{job_id}"
    
    while True:
        poll_res = requests.get(poll_url)
        poll_data = poll_res.json()
        if poll_data.get("status") == "completed":
            logging.info("--- Async Endpoint ---")
            logging.info(f"ID: {poll_data.get('job_id')}")
            logging.info(f"Response: {poll_data.get('response')}")
            break
        time.sleep(1)

else:
    logging.error(f"Failed to initiate async request: {response.status_code} - {response.text}")


# curl -X POST "https://lm-gateway.git-pratap-shrey.online/api/async" -H "Content-Type: application/json" -d '{"provider":"ollama","model":"gemma4:cloud","messages":[{"role":"user","content":"Hello, i am obi wan kenobi."}]}'

# curl -X GET https://lm-gateway.git-pratap-shrey.online/{job_id}
