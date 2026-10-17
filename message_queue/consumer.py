import logging
import json
import os
import time
import pika
from typing import Any
from router import Router
from result_store.result_store import Result_store
from utils.logging_utils import job_log_file
import config
from message_queue.fallback import requeue, escalate_provider


class Consumer:
    def __init__(self) -> None:
        host = os.getenv("RABBITMQ_HOST", "localhost")
        try:
            logging.debug(f"Consumer: Connecting to RabbitMQ at host '{host}'...")
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=host)
            )
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue="tasks", durable=True)
            logging.debug("Consumer: Connected and 'tasks' queue declared.")
        except Exception as e:
            logging.error(f"Consumer: Failed to connect to RabbitMQ at '{host}': {e}")
            raise

    def start_consuming(self) -> None:
        self.channel.basic_qos(prefetch_count=1)
        self.channel.basic_consume(
            queue="tasks",
            on_message_callback=self.callback
        )

        logging.info("Consumer: Starting to consume messages from 'tasks' queue.")
        logging.info("Waiting for messages...")
        self.channel.start_consuming()

    def callback(self, ch: Any, method: Any, properties: Any, body: bytes) -> None:
        try:
            payload = json.loads(body.decode())
        except Exception as exc:
            logging.error(f"Consumer: Failed to decode incoming message JSON: {exc}")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        job_id = payload.get("job_id", "unknown")

        # Retry / fallback state (injected into payload so it survives re-queuing)
        retry_count    = payload.get("retry_count", 0)
        fallback_index = payload.get("fallback_index", 0)
        provider = payload.get("input", {}).get("provider", "unknown")
        model = payload.get("input", {}).get("model", "unknown")

        try:
            with job_log_file(job_id):
                logging.info(
                    f"Received job ID {job_id} "
                    f"(fallback={fallback_index}, retry={retry_count}/{config.MAX_RETRIES})."
                )
                logging.info(f"Consumer: Processing job ID {job_id} with provider '{provider}' and model '{model}'.")

                Result_store().update_job(job_id, status="processing", output=None)

                start_time = time.perf_counter()
                try:
                    payload["output"] = Router().route(payload["input"])
                    payload["status"] = "completed"
                    elapsed = time.perf_counter() - start_time
                    logging.info(f"Processed job ID {job_id} in {elapsed:.2f}s.")
                    logging.info(f"Processed job ID {job_id}.")
                    Result_store().update_job(job_id, status="completed", output=payload["output"])

                except Exception as e:
                    elapsed = time.perf_counter() - start_time
                    logging.error(f"Failed job ID {job_id} after {elapsed:.2f}s (fallback={fallback_index}): {e}")
                    logging.error(f"Failed job ID {job_id} (fallback={fallback_index}): {e}")

                    if retry_count < config.MAX_RETRIES:
                        payload["retry_count"] = retry_count + 1
                        logging.info(
                            f"Requeueing job ID {job_id} "
                            f"(retry {retry_count + 1}/{config.MAX_RETRIES})."
                        )
                        Result_store().update_job(job_id, status="queued", output=None)
                        requeue(self.channel, payload)

                    elif escalate_provider(payload):
                        logging.info(f"Consumer: Requeuing job ID {job_id} after provider escalation.")
                        Result_store().update_job(job_id, status="queued", output=None)
                        requeue(self.channel, payload)

                    else:
                        logging.error(f"All providers exhausted for job ID {job_id}. Marking failed.")
                        Result_store().update_job(job_id, status="failed", output=None)

        except Exception as outer_exc:
            # Safety net: something outside the routing logic blew up (e.g. DB error, log file error).
            # Always mark failed so the job doesn't stay stuck in 'processing'.
            logging.error(f"Consumer: Unexpected outer error for job ID {job_id}: {outer_exc}")
            try:
                Result_store().update_job(job_id, status="failed", output=None)
            except Exception:
                pass  # DB itself may be broken; don't let this prevent the ack

        finally:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logging.debug(f"Consumer: Acknowledged delivery tag {method.delivery_tag} for job ID {job_id}.")

    def close_connection(self) -> None:
        try:
            self.connection.close()
            logging.info("Consumer: Connection closed.")
        except Exception as e:
            logging.warning(f"Consumer: Error while closing connection: {e}")