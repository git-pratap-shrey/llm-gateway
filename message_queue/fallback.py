import json
import logging
import pika
from typing import Any
import config

# Ordered list of (provider, model) fallback tiers, highest priority first
PROVIDER_TIERS = [
    (config.PRIORITY_1, config.PRIORITY_1_MODEL),
    (config.PRIORITY_2, config.PRIORITY_2_MODEL),
    (config.PRIORITY_3, config.PRIORITY_3_MODEL),
]


def requeue(channel: Any, payload: dict[str, Any]) -> None:
    """Re-publish the payload back onto the tasks queue."""
    channel.basic_publish(
        exchange="",
        routing_key="tasks",
        body=json.dumps(payload),
        properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent),
    )
    logging.info(f"Requeued job ID {payload['job_id']}.")


def escalate_provider(payload: dict[str, Any]) -> bool:
    """
    Advance payload to the next fallback provider and reset retry_count.
    Fallback order is always PRIORITY_1 → PRIORITY_2 → PRIORITY_3,
    with the original provider skipped (it already failed).
    Returns True if escalation was possible, False if all providers exhausted.
    """
    original_provider = payload.setdefault("original_provider", payload["input"]["provider"])
    fallback_list = [(p, m) for p, m in PROVIDER_TIERS if p != original_provider]

    fallback_index = payload.get("fallback_index", 0)
    if fallback_index >= len(fallback_list):
        return False

    next_provider, next_model = fallback_list[fallback_index]
    payload["fallback_index"]    = fallback_index + 1
    payload["retry_count"]       = 0
    payload["input"]["provider"] = next_provider
    payload["input"]["model"]    = next_model

    logging.info(
        f"Escalating job ID {payload['job_id']} "
        f"(fallback {fallback_index + 1}/{len(fallback_list)}: {next_provider}/{next_model})."
    )
    return True

