import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from main import app
from validation import Schema

client = TestClient(app)


def test_process_async():
    with patch("main.Worker") as mock_worker_class, \
         patch("main.Result_store") as mock_result_store_class, \
         patch("main.uuid7") as mock_uuid7:

        mock_uuid7.return_value = "00000000-0000-0000-0000-000000000000"
        mock_worker_instance = MagicMock()
        mock_worker_class.return_value = mock_worker_instance

        mock_store_instance = MagicMock()
        mock_result_store_class.return_value = mock_store_instance

        payload = {
            "provider": "ollama_cloud",
            "model": "gemma4:cloud",
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
        assert produced_msg["input"]["provider"] == "ollama_cloud"


def test_process_sync():
    with patch("main.Router") as mock_router_class:
        mock_router_instance = MagicMock()
        mock_router_class.return_value = mock_router_instance
        mock_router_instance.route.return_value = "Mocked sync response"

        payload = {
            "provider": "gemini",
            "model": "gemma-4-31b-it",
            "messages": [
                {"role": "user", "content": "Hello sync"}
            ]
        }

        response = client.post("/api/sync", json=payload)

        assert response.status_code == 200
        assert response.json() == "Mocked sync response"
        mock_router_instance.route.assert_called_once()


def test_process_sync_openrouter():
    with patch("main.Router") as mock_router_class:
        mock_router_instance = MagicMock()
        mock_router_class.return_value = mock_router_instance
        mock_router_instance.route.return_value = "Openrouter response"

        payload = {
            "provider": "openrouter",
            "model": "meta-llama/llama-3",
            "messages": [{"role": "user", "content": "Hello"}]
        }

        response = client.post("/api/sync", json=payload)
        assert response.status_code == 200
        assert response.json() == "Openrouter response"


def test_process_sync_router_error_500():
    """Any generic exception from Router results in a 500."""
    with patch("main.Router") as mock_router_class:
        mock_router_class.return_value.route.side_effect = RuntimeError("upstream failure")

        payload = {
            "provider": "gemini",
            "model": "gemma-4-31b-it",
            "messages": [{"role": "user", "content": "Hello"}]
        }

        response = client.post("/api/sync", json=payload)
        assert response.status_code == 500
        assert response.json()["detail"]["message"] == "Job processing failed."


def test_process_sync_model_not_found_404():
    """OllamaModelNotAvailableError from Router results in a 404."""

    class OllamaModelNotAvailableError(Exception):
        pass

    with patch("main.Router") as mock_router_class:
        mock_router_class.return_value.route.side_effect = OllamaModelNotAvailableError("model xyz not found")

        payload = {
            "provider": "ollama_cloud",
            "model": "no-such-model",
            "messages": [{"role": "user", "content": "Hello"}]
        }

        response = client.post("/api/sync", json=payload)
        assert response.status_code == 404
        assert "model xyz not found" in response.json()["detail"]["message"]


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
    """When Result_store returns None the endpoint must raise HTTP 404."""
    with patch("main.Result_store") as mock_result_store_class:
        mock_store_instance = MagicMock()
        mock_result_store_class.return_value = mock_store_instance
        mock_store_instance.check_status.return_value = None

        response = client.get("/00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404
        detail = response.json()["detail"]
        assert detail["message"] == "Job not found."
        mock_store_instance.check_status.assert_called_once_with("00000000-0000-0000-0000-000000000000")


def test_process_async_broker_unavailable():
    with patch("main.Worker") as mock_worker_class, \
         patch("main.Result_store") as mock_result_store_class:

        mock_store_instance = MagicMock()
        mock_result_store_class.return_value = mock_store_instance

        mock_worker_class.return_value.produce_message.side_effect = HTTPException(
            503, detail={"job_id": None, "message": "rabbitmq client not available"}
        )

        payload = {
            "provider": "ollama_cloud",
            "model": "gemma4:cloud",
            "messages": [{"role": "user", "content": "hi"}]
        }
        response = client.post("/api/async", json=payload)

        assert response.status_code == 503
        assert response.json()["detail"] == {"job_id": None, "message": "rabbitmq client not available"}


def test_process_async_db_record_created():
    """Result_store.create_job is called with the job_id before producing to queue."""
    with patch("main.Worker") as mock_worker_class, \
         patch("main.Result_store") as mock_result_store_class, \
         patch("main.uuid7") as mock_uuid7:

        mock_uuid7.return_value = "test-job-id"
        mock_worker_class.return_value.produce_message.return_value = None
        mock_store = MagicMock()
        mock_result_store_class.return_value = mock_store

        payload = {
            "provider": "ollama_cloud",
            "model": "gemma4:cloud",
            "messages": [{"role": "user", "content": "hi"}]
        }
        response = client.post("/api/async", json=payload)

        assert response.status_code == 200
        mock_store.create_job.assert_called_once_with("test-job-id", {
            "provider": "ollama_cloud",
            "model": "gemma4:cloud",
            "messages": [{"role": "user", "content": "hi"}],
            "parameters": None,
            "stream": False,
        })


def test_invalid_payload_returns_422():
    """Missing required fields return FastAPI's 422."""
    response = client.post("/api/async", json={"model": "gemma"})
    assert response.status_code == 422

    response = client.post("/api/sync", json={"provider": "gemini"})
    assert response.status_code == 422


def test_invalid_provider_returns_422():
    """An unknown provider value is rejected by Pydantic with a 422."""
    payload = {
        "provider": "unknown_provider",
        "model": "gemma",
        "messages": [{"role": "user", "content": "Hello"}]
    }
    response = client.post("/api/async", json=payload)
    assert response.status_code == 422
