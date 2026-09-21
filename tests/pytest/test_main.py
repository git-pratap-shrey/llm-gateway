import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from main import app
from validation import Schema

client = TestClient(app)

def test_process_async():
    with patch("main.Worker") as mock_worker_class, \
         patch("main.uuid7") as mock_uuid7:
        
        mock_uuid7.return_value = "00000000-0000-0000-0000-000000000000"
        mock_worker_instance = MagicMock()
        mock_worker_class.return_value = mock_worker_instance

        payload = {
            "provider": "ollama",
            "model": "gemma",
            "messages": [
                {"role": "user", "content": "Hello async"}
            ]
        }
        
        response = client.post("/api/async", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == "00000000-0000-0000-0000-000000000000"
        assert data["message"] == "Job queued successfully."
        
        mock_worker_instance.produce_message.assert_called_once()
        produced_msg = mock_worker_instance.produce_message.call_args[0][0]
        assert produced_msg["job_id"] == "00000000-0000-0000-0000-000000000000"
        assert produced_msg["status"] == "queued"
        assert produced_msg["output"] is None
        assert produced_msg["input"]["provider"] == "ollama"

def test_process_sync():
    with patch("main.Router") as mock_router_class:
        mock_router_instance = MagicMock()
        mock_router_class.return_value = mock_router_instance
        mock_router_instance.route.return_value = "Mocked sync response"

        payload = {
            "provider": "ollama",
            "model": "gemma",
            "messages": [
                {"role": "user", "content": "Hello sync"}
            ]
        }
        
        response = client.post("/api/sync", json=payload)
        
        assert response.status_code == 200
        assert response.json() == "Mocked sync response"
        mock_router_instance.route.assert_called_once()

def test_get_item():
    with patch("main.Result_store") as mock_result_store_class:
        mock_store_instance = MagicMock()
        mock_result_store_class.return_value = mock_store_instance
        mock_store_instance.check_status.return_value = {"status": "completed"}
        
        response = client.get("/00000000-0000-0000-0000-000000000000")
        
        assert response.status_code == 200
        assert response.json() == {"status": "completed"}
        mock_store_instance.check_status.assert_called_once_with("00000000-0000-0000-0000-000000000000")

def test_get_item_not_found():
    with patch("main.Result_store") as mock_result_store_class:
        mock_store_instance = MagicMock()
        mock_result_store_class.return_value = mock_store_instance
        mock_store_instance.check_status.return_value = None

        response = client.get("00000000-0000-0000-0000-000000000000")

        assert response.status_code == 200
        assert response.json() is None
        mock_store_instance.check_status.assert_called_once_with("00000000-0000-0000-0000-000000000000")

def test_process_async_broker_unavailable():
    with patch("main.Worker") as mock_worker_class:
        mock_worker_class.return_value.produce_message.side_effect = HTTPException(
            503, detail={"job_id": None, "message": "rabbitmq client not available"}
        )

        payload = {"provider": "ollama", "model": "gemma", "messages": [{"role": "user", "content": "hi"}]}
        response = client.post("/api/async", json=payload)

        assert response.status_code == 503
        assert response.json()["detail"] == {"job_id": None, "message": "rabbitmq client not available"}
