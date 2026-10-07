"""Unit tests for message_queue.producer.Producer.

All pika network calls are mocked so no RabbitMQ instance is required.
"""
import json
from unittest.mock import MagicMock, patch, call

import pytest

from message_queue.producer import Producer


@pytest.fixture()
def mocked_pika():
    """Patches pika.BlockingConnection and returns (mock_connection, mock_channel)."""
    with patch("message_queue.producer.pika.BlockingConnection") as mock_conn_cls:
        mock_channel = MagicMock()
        mock_conn = MagicMock()
        mock_conn.channel.return_value = mock_channel
        mock_conn_cls.return_value = mock_conn
        yield mock_conn_cls, mock_conn, mock_channel


# ---------------------------------------------------------------------------
# __init__ — connection setup
# ---------------------------------------------------------------------------

def test_producer_declares_durable_tasks_queue(mocked_pika):
    _, _, mock_channel = mocked_pika

    Producer()

    mock_channel.queue_declare.assert_called_once_with(queue="tasks", durable=True)


def test_producer_connects_to_configured_host(mocked_pika):
    mock_conn_cls, _, _ = mocked_pika

    with patch.dict("os.environ", {"RABBITMQ_HOST": "broker.internal"}):
        Producer()

    call_args = mock_conn_cls.call_args
    params = call_args[0][0]  # first positional arg is ConnectionParameters
    assert params.host == "broker.internal"


def test_producer_defaults_to_localhost(mocked_pika):
    import os
    mock_conn_cls, _, _ = mocked_pika

    # Ensure RABBITMQ_HOST is unset
    env = {k: v for k, v in os.environ.items() if k != "RABBITMQ_HOST"}
    with patch.dict("os.environ", env, clear=True):
        Producer()

    call_args = mock_conn_cls.call_args
    params = call_args[0][0]
    assert params.host == "localhost"


# ---------------------------------------------------------------------------
# send_message
# ---------------------------------------------------------------------------

def test_send_message_publishes_to_tasks_queue(mocked_pika):
    _, _, mock_channel = mocked_pika
    producer = Producer()

    payload = {
        "job_id": "test-job-abc",
        "input": {"provider": "gemini", "model": "gemma-4-31b-it"},
        "status": "queued",
        "output": None,
    }

    producer.send_message(payload)

    mock_channel.basic_publish.assert_called_once()
    kwargs = mock_channel.basic_publish.call_args.kwargs
    assert kwargs["exchange"] == ""
    assert kwargs["routing_key"] == "tasks"
    assert json.loads(kwargs["body"]) == payload


def test_send_message_uses_persistent_delivery(mocked_pika):
    _, _, mock_channel = mocked_pika
    producer = Producer()

    payload = {"job_id": "p-job", "input": {}, "status": "queued", "output": None}
    producer.send_message(payload)

    kwargs = mock_channel.basic_publish.call_args.kwargs
    # pika.DeliveryMode.Persistent == 2
    assert kwargs["properties"].delivery_mode == 2


def test_send_message_closes_connection(mocked_pika):
    _, mock_conn, _ = mocked_pika
    producer = Producer()

    payload = {"job_id": "close-job", "input": {}, "status": "queued", "output": None}
    producer.send_message(payload)

    mock_conn.close.assert_called_once()


# ---------------------------------------------------------------------------
# close_connection
# ---------------------------------------------------------------------------

def test_close_connection_delegates_to_pika(mocked_pika):
    _, mock_conn, _ = mocked_pika
    producer = Producer()

    producer.close_connection()

    mock_conn.close.assert_called()
