import json
from unittest.mock import MagicMock, patch
import pytest

import config
from message_queue.fallback import PROVIDER_TIERS, escalate_provider, requeue
from message_queue.consumer import Consumer


# ============================================================================
# Unit Tests for message_queue.fallback
# ============================================================================

def test_requeue_publishes_to_tasks_queue():
    """Verify that requeue publishes the payload persistently to the 'tasks' queue."""
    mock_channel = MagicMock()
    payload = {
        "job_id": "test-job-123",
        "input": {"provider": "ollama", "model": "gemma"},
        "retry_count": 1,
    }

    requeue(mock_channel, payload)

    mock_channel.basic_publish.assert_called_once()
    call_args = mock_channel.basic_publish.call_args
    assert call_args.kwargs["exchange"] == ""
    assert call_args.kwargs["routing_key"] == "tasks"
    assert json.loads(call_args.kwargs["body"]) == payload
    properties = call_args.kwargs["properties"]
    assert properties.delivery_mode == 2  # pika.DeliveryMode.Persistent


def test_escalate_provider_priority_1_start():
    """
    When starting at PRIORITY_1 (e.g., ollama):
    - 1st escalation: switches to PRIORITY_2
    - 2nd escalation: switches to PRIORITY_3
    - 3rd escalation: returns False (all fallbacks exhausted)
    """
    payload = {
        "job_id": "job-1",
        "input": {
            "provider": config.PRIORITY_1,
            "model": config.PRIORITY_1_MODEL,
            "messages": [{"role": "user", "content": "hi"}],
        },
        "retry_count": 3,
    }

    # First escalation -> should go to PRIORITY_2
    assert escalate_provider(payload) is True
    assert payload["original_provider"] == config.PRIORITY_1
    assert payload["fallback_index"] == 1
    assert payload["retry_count"] == 0
    assert payload["input"]["provider"] == config.PRIORITY_2
    assert payload["input"]["model"] == config.PRIORITY_2_MODEL

    # Simulate retries reaching max again
    payload["retry_count"] = config.MAX_RETRIES

    # Second escalation -> should go to PRIORITY_3
    assert escalate_provider(payload) is True
    assert payload["original_provider"] == config.PRIORITY_1
    assert payload["fallback_index"] == 2
    assert payload["retry_count"] == 0
    assert payload["input"]["provider"] == config.PRIORITY_3
    assert payload["input"]["model"] == config.PRIORITY_3_MODEL

    # Simulate retries reaching max again
    payload["retry_count"] = config.MAX_RETRIES

    # Third escalation -> all providers exhausted
    assert escalate_provider(payload) is False
    # State should remain at the last attempted provider
    assert payload["input"]["provider"] == config.PRIORITY_3


def test_escalate_provider_priority_2_start():
    """
    When starting at PRIORITY_2 (e.g., openrouter):
    - 1st escalation: switches to PRIORITY_1 (best available fallback)
    - 2nd escalation: switches to PRIORITY_3
    - 3rd escalation: returns False (exhausted)
    """
    payload = {
        "job_id": "job-2",
        "input": {
            "provider": config.PRIORITY_2,
            "model": config.PRIORITY_2_MODEL,
            "messages": [{"role": "user", "content": "hi"}],
        },
        "retry_count": 3,
    }

    # First escalation -> jumps to PRIORITY_1
    assert escalate_provider(payload) is True
    assert payload["original_provider"] == config.PRIORITY_2
    assert payload["fallback_index"] == 1
    assert payload["retry_count"] == 0
    assert payload["input"]["provider"] == config.PRIORITY_1
    assert payload["input"]["model"] == config.PRIORITY_1_MODEL

    # Second escalation -> jumps to PRIORITY_3
    assert escalate_provider(payload) is True
    assert payload["fallback_index"] == 2
    assert payload["retry_count"] == 0
    assert payload["input"]["provider"] == config.PRIORITY_3
    assert payload["input"]["model"] == config.PRIORITY_3_MODEL

    # Third escalation -> exhausted
    assert escalate_provider(payload) is False


def test_escalate_provider_priority_3_start():
    """
    When starting at PRIORITY_3 (e.g., gemini):
    - 1st escalation: switches to PRIORITY_1 (best available fallback)
    - 2nd escalation: switches to PRIORITY_2
    - 3rd escalation: returns False (exhausted)
    """
    payload = {
        "job_id": "job-3",
        "input": {
            "provider": config.PRIORITY_3,
            "model": config.PRIORITY_3_MODEL,
            "messages": [{"role": "user", "content": "hi"}],
        },
        "retry_count": 3,
    }

    # First escalation -> jumps to PRIORITY_1
    assert escalate_provider(payload) is True
    assert payload["original_provider"] == config.PRIORITY_3
    assert payload["fallback_index"] == 1
    assert payload["retry_count"] == 0
    assert payload["input"]["provider"] == config.PRIORITY_1
    assert payload["input"]["model"] == config.PRIORITY_1_MODEL

    # Second escalation -> jumps to PRIORITY_2
    assert escalate_provider(payload) is True
    assert payload["fallback_index"] == 2
    assert payload["retry_count"] == 0
    assert payload["input"]["provider"] == config.PRIORITY_2
    assert payload["input"]["model"] == config.PRIORITY_2_MODEL

    # Third escalation -> exhausted
    assert escalate_provider(payload) is False


def test_escalate_provider_preserves_existing_original_provider():
    """If original_provider is already recorded, escalate_provider preserves it."""
    payload = {
        "job_id": "job-4",
        "original_provider": config.PRIORITY_1,
        "fallback_index": 1,
        "input": {
            "provider": config.PRIORITY_2,
            "model": config.PRIORITY_2_MODEL,
        },
        "retry_count": 3,
    }

    assert escalate_provider(payload) is True
    assert payload["original_provider"] == config.PRIORITY_1
    assert payload["fallback_index"] == 2
    assert payload["input"]["provider"] == config.PRIORITY_3


# ============================================================================
# Unit Tests for message_queue.consumer retry & fallback integration
# ============================================================================

@pytest.fixture
def consumer_instance():
    """Create a Consumer instance with pika connection mocked."""
    with patch("pika.BlockingConnection") as mock_conn:
        mock_channel = MagicMock()
        mock_conn.return_value.channel.return_value = mock_channel
        consumer = Consumer()
        consumer.channel = mock_channel
        return consumer


def test_consumer_callback_success(consumer_instance):
    """Successful route call completes the job and acks the message without retrying."""
    payload = {
        "job_id": "job-success",
        "input": {"provider": "ollama", "model": "gemma", "messages": []},
    }
    body = json.dumps(payload).encode()
    mock_ch = MagicMock()
    mock_method = MagicMock(delivery_tag=101)

    with patch("message_queue.consumer.Router") as mock_router_cls, \
         patch("message_queue.consumer.Result_store") as mock_store_cls, \
         patch("message_queue.consumer.job_log_file"), \
         patch("message_queue.consumer.requeue") as mock_requeue:

        mock_router_cls.return_value.route.return_value = "Generated response"
        mock_store = mock_store_cls.return_value

        consumer_instance.callback(mock_ch, mock_method, None, body)

        # Result store updated to processing, then completed
        assert mock_store.update_job.call_count == 2
        mock_store.update_job.assert_any_call("job-success", status="processing", output=None)
        mock_store.update_job.assert_any_call("job-success", status="completed", output="Generated response")

        # No requeue on success
        mock_requeue.assert_not_called()

        # Ack must be called
        mock_ch.basic_ack.assert_called_once_with(delivery_tag=101)


def test_consumer_callback_retry_on_same_provider_below_max(consumer_instance):
    """When router fails and retry_count < MAX_RETRIES, requeue on same provider with retry_count incremented."""
    payload = {
        "job_id": "job-retry",
        "input": {"provider": "ollama", "model": "gemma", "messages": []},
        "retry_count": 1,
    }
    body = json.dumps(payload).encode()
    mock_ch = MagicMock()
    mock_method = MagicMock(delivery_tag=102)

    with patch("message_queue.consumer.Router") as mock_router_cls, \
         patch("message_queue.consumer.Result_store") as mock_store_cls, \
         patch("message_queue.consumer.job_log_file"), \
         patch("message_queue.consumer.requeue") as mock_requeue:

        mock_router_cls.return_value.route.side_effect = RuntimeError("Ollama connection error")
        mock_store = mock_store_cls.return_value

        consumer_instance.callback(mock_ch, mock_method, None, body)

        # Result store updated to processing, then queued
        mock_store.update_job.assert_any_call("job-retry", status="processing", output=None)
        mock_store.update_job.assert_any_call("job-retry", status="queued", output=None)

        # Requeue called with retry_count incremented
        mock_requeue.assert_called_once()
        requeued_payload = mock_requeue.call_args[0][1]
        assert requeued_payload["retry_count"] == 2
        assert requeued_payload["input"]["provider"] == "ollama"

        # Ack must still be sent for the current message
        mock_ch.basic_ack.assert_called_once_with(delivery_tag=102)


def test_consumer_callback_escalate_provider_at_max_retries(consumer_instance):
    """When retry_count reaches MAX_RETRIES, escalate to the next provider and requeue."""
    payload = {
        "job_id": "job-escalate",
        "input": {"provider": config.PRIORITY_1, "model": config.PRIORITY_1_MODEL},
        "retry_count": config.MAX_RETRIES,
    }
    body = json.dumps(payload).encode()
    mock_ch = MagicMock()
    mock_method = MagicMock(delivery_tag=103)

    with patch("message_queue.consumer.Router") as mock_router_cls, \
         patch("message_queue.consumer.Result_store") as mock_store_cls, \
         patch("message_queue.consumer.job_log_file"), \
         patch("message_queue.consumer.requeue") as mock_requeue:

        mock_router_cls.return_value.route.side_effect = RuntimeError("Provider down")
        mock_store = mock_store_cls.return_value

        consumer_instance.callback(mock_ch, mock_method, None, body)

        # Result store status queued
        mock_store.update_job.assert_any_call("job-escalate", status="queued", output=None)

        # Requeue called with next provider and reset retry_count
        mock_requeue.assert_called_once()
        requeued_payload = mock_requeue.call_args[0][1]
        assert requeued_payload["retry_count"] == 0
        assert requeued_payload["input"]["provider"] == config.PRIORITY_2
        assert requeued_payload["input"]["model"] == config.PRIORITY_2_MODEL

        # Original message acked
        mock_ch.basic_ack.assert_called_once_with(delivery_tag=103)


def test_consumer_callback_marks_failed_when_all_providers_exhausted(consumer_instance):
    """When max retries reached on the final fallback provider, mark job as failed."""
    payload = {
        "job_id": "job-exhausted",
        "original_provider": config.PRIORITY_1,
        "fallback_index": 2,  # Already used both fallbacks (openrouter, gemini)
        "input": {"provider": config.PRIORITY_3, "model": config.PRIORITY_3_MODEL},
        "retry_count": config.MAX_RETRIES,
    }
    body = json.dumps(payload).encode()
    mock_ch = MagicMock()
    mock_method = MagicMock(delivery_tag=104)

    with patch("message_queue.consumer.Router") as mock_router_cls, \
         patch("message_queue.consumer.Result_store") as mock_store_cls, \
         patch("message_queue.consumer.job_log_file"), \
         patch("message_queue.consumer.requeue") as mock_requeue:

        mock_router_cls.return_value.route.side_effect = RuntimeError("All providers dead")
        mock_store = mock_store_cls.return_value

        consumer_instance.callback(mock_ch, mock_method, None, body)

        # Job marked failed
        mock_store.update_job.assert_any_call("job-exhausted", status="failed", output=None)

        # Should NOT requeue
        mock_requeue.assert_not_called()

        # Original message acked
        mock_ch.basic_ack.assert_called_once_with(delivery_tag=104)


def test_full_retry_and_fallback_lifecycle(consumer_instance):
    """
    Simulate the end-to-end lifecycle across all retries and all 3 providers.
    Ensures:
      - 3 retries on PRIORITY_1
      - Escalation to PRIORITY_2, followed by 3 retries
      - Escalation to PRIORITY_3, followed by 3 retries
      - Final failure marking
    """
    mock_ch = MagicMock()
    mock_method = MagicMock(delivery_tag=1)

    payload = {
        "job_id": "job-e2e-fail",
        "input": {"provider": config.PRIORITY_1, "model": config.PRIORITY_1_MODEL},
    }

    history = []

    with patch("message_queue.consumer.Router") as mock_router_cls, \
         patch("message_queue.consumer.Result_store") as mock_store_cls, \
         patch("message_queue.consumer.job_log_file"):

        mock_router_cls.return_value.route.side_effect = RuntimeError("Failure")
        mock_store = mock_store_cls.return_value

        # Use real requeue interception to capture state across simulated deliveries
        def fake_requeue(channel, p):
            # Record a deep-copy snapshot
            history.append(json.loads(json.dumps(p)))

        with patch("message_queue.consumer.requeue", side_effect=fake_requeue):
            current_body = json.dumps(payload).encode()

            # Maximum possible steps = (MAX_RETRIES + 1) * 3 providers
            # For MAX_RETRIES=3: 4 attempts per provider * 3 providers = 12 callbacks
            max_steps = (config.MAX_RETRIES + 1) * 3

            for step in range(max_steps):
                consumer_instance.callback(mock_ch, mock_method, None, current_body)
                if not history or len(history) <= step:
                    # No requeue happened; job reached terminal state
                    break
                current_body = json.dumps(history[-1]).encode()

        # Should have performed 11 requeues before finally marking failed on the 12th attempt
        assert len(history) == 11

        # Check provider transitions in requeued history:
        # History index 0, 1, 2: retries 1, 2, 3 on PRIORITY_1
        assert history[0]["input"]["provider"] == config.PRIORITY_1
        assert history[0]["retry_count"] == 1
        assert history[1]["input"]["provider"] == config.PRIORITY_1
        assert history[1]["retry_count"] == 2
        assert history[2]["input"]["provider"] == config.PRIORITY_1
        assert history[2]["retry_count"] == 3

        # History index 3: Escalated to PRIORITY_2, retry_count=0
        assert history[3]["input"]["provider"] == config.PRIORITY_2
        assert history[3]["retry_count"] == 0

        # History index 4, 5, 6: retries 1, 2, 3 on PRIORITY_2
        assert history[4]["input"]["provider"] == config.PRIORITY_2
        assert history[4]["retry_count"] == 1
        assert history[5]["input"]["provider"] == config.PRIORITY_2
        assert history[5]["retry_count"] == 2
        assert history[6]["input"]["provider"] == config.PRIORITY_2
        assert history[6]["retry_count"] == 3

        # History index 7: Escalated to PRIORITY_3, retry_count=0
        assert history[7]["input"]["provider"] == config.PRIORITY_3
        assert history[7]["retry_count"] == 0

        # History index 8, 9, 10: retries 1, 2, 3 on PRIORITY_3
        assert history[8]["input"]["provider"] == config.PRIORITY_3
        assert history[8]["retry_count"] == 1
        assert history[9]["input"]["provider"] == config.PRIORITY_3
        assert history[9]["retry_count"] == 2
        assert history[10]["input"]["provider"] == config.PRIORITY_3
        assert history[10]["retry_count"] == 3

        # Terminal state: update_job called with "failed"
        mock_store.update_job.assert_any_call("job-e2e-fail", status="failed", output=None)
