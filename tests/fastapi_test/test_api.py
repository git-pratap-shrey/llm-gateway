import time

import pytest
from fastapi.testclient import TestClient

from main import app


client = TestClient(app)

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


def test_async():
    # Queue job
    response = client.post("/api/async", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert "job_id" in data
    assert data["message"] == "Job queued successfully."

    job_id = data["job_id"]

    # Poll until completed
    for _ in range(30):
        response = client.get(f"/{job_id}")

        assert response.status_code == 200

        result = response.json()

        print(result)

        if result.get("status") == "completed":
            break

        time.sleep(1)

    else:
        pytest.fail("Job did not complete within 30 seconds")


def test_sync():
    response = client.post("/api/sync", json=payload)

    assert response.status_code == 200

    print(response.json())