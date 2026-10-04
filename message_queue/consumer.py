import logging
import json
import os
import pika
from typing import Any
from router import Router
from result_store.result_store import Result_store
from utils.logging_utils import job_log_file
import config
from message_queue.fallback import requeue, escalate_provider


class Consumer:
    def __init__(self) -> None:
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=os.getenv("RABBITMQ_HOST", "localhost"))
        )
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue="tasks", durable=True)

    def start_consuming(self) -> None:
        self.channel.basic_consume(
            queue="tasks",
            on_message_callback=self.callback
        )

        logging.info("Waiting for messages...")
        self.channel.start_consuming()

    def callback(self, ch: Any, method: Any, properties: Any, body: bytes) -> None:
        payload = json.loads(body.decode())
        job_id = payload["job_id"]

        # Retry / fallback state (injected into payload so it survives re-queuing)
        retry_count    = payload.get("retry_count", 0)
        fallback_index = payload.get("fallback_index", 0)

        with job_log_file(job_id):
            logging.info(
                f"Received job ID {job_id} "
                f"(fallback={fallback_index}, retry={retry_count}/{config.MAX_RETRIES})."
            )

            Result_store().update_job(job_id, status="processing", output=None)

            try:
                payload["output"] = Router().route(payload["input"])
                payload["status"] = "completed"
                logging.info(f"Processed job ID {job_id}.")
                Result_store().update_job(job_id, status="completed", output=payload["output"])

            except Exception as e:
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
                    Result_store().update_job(job_id, status="queued", output=None)
                    requeue(self.channel, payload)

                else:
                    logging.error(f"All providers exhausted for job ID {job_id}. Marking failed.")
                    Result_store().update_job(job_id, status="failed", output=None)

        ch.basic_ack(delivery_tag=method.delivery_tag)

    def close_connection(self) -> None:
        self.connection.close()