import json
import os
import sys
import pytest
from typing import Any

# Add the root of the project to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app, raise_server_exceptions=False)

# Load the inputs from the JSON file
INPUTS_FILE = os.path.join(os.path.dirname(__file__), "test_inputs.json")
with open(INPUTS_FILE, "r") as f:
    test_payloads = json.load(f)

@pytest.mark.parametrize("payload", test_payloads)
def test_simulate_curl_sync_endpoint(payload: dict[str, Any]) -> None:
    """
    Simulates a curl request to the /api/sync endpoint for each provider
    in the test_inputs.json file and saves the output.
    """
    # Send request using TestClient (simulating the curl command)
    response = client.post("/api/sync", json=payload)
    
    # Try to parse the response as JSON, fallback to raw text
    try:
        output_data = response.json()
    except Exception:
        output_data = response.text

    # Prepare data to be written to the file
    result = {
        "input": payload,
        "status_code": response.status_code,
        "output": output_data
    }
    
    # Define a unique output file path per provider
    provider_name = payload.get("provider", "unknown")
    output_file_path = os.path.join(os.path.dirname(__file__), f"sync_test_output_{provider_name}.json")
    
    # Write the input and output to the file
    with open(output_file_path, "w") as f:
        json.dump(result, f, indent=4)
        
    # Assert that the file was created successfully
    assert os.path.exists(output_file_path)

