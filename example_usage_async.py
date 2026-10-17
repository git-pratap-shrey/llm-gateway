import logging
import requests
import time

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

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
logging.info(f"Submitting async request for model '{payload['model']}'...")
response = requests.post("https://lm-gateway.git-pratap-shrey.online/api/async", json=payload)

## start polling for the result:
if response.status_code == 200:
    job_id = response.json()["job_id"]
    logging.info(f"Async request initiated successfully. Job ID: {job_id}")
    poll_url = f"https://lm-gateway.git-pratap-shrey.online/{job_id}"
    
    while True:
        poll_res = requests.get(poll_url)
        poll_data = poll_res.json()
        status = poll_data.get("status")
        if status == "completed":
            logging.info("--- Async Endpoint ---")
            logging.info(f"ID: {poll_data.get('job_id')}")
            logging.info(f"Response: {poll_data.get('response')}")
            break
        elif status == "failed":
            logging.error(f"Job {job_id} failed on the gateway: {poll_data}")
            break
        else:
            logging.info(f"Job {job_id} status: {status}. Waiting...")
        time.sleep(1)

else:
    logging.error(f"Failed to initiate async request: {response.status_code} - {response.text}")


# curl -X POST "https://lm-gateway.git-pratap-shrey.online/api/async" -H "Content-Type: application/json" -d '{"provider":"ollama","model":"gemma4:cloud","messages":[{"role":"user","content":"Hello, i am obi wan kenobi."}]}'

# curl -X GET https://lm-gateway.git-pratap-shrey.online/{job_id}
