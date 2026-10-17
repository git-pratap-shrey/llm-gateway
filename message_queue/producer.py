import logging
import os
import pika
import json
from typing import Any

class Producer:
    def __init__(self) -> None:
        host = os.getenv("RABBITMQ_HOST", "localhost")
        try:
            logging.debug(f"Producer: Connecting to RabbitMQ at host '{host}'...")
            self.connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=host)
            )
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue="tasks", durable=True)
            logging.debug("Producer: Connected and 'tasks' queue declared.")
        except Exception as e:
            logging.error(f"Producer: Failed to connect to RabbitMQ at '{host}': {e}")
            raise

    def send_message(self, payload: dict[str, Any]) -> None:
        job_id = payload.get("job_id", "unknown")
        try:
            logging.info(f"Producer: Publishing job ID {job_id} to queue 'tasks'.")
            self.channel.basic_publish(
                exchange="",
                routing_key="tasks",
                body=json.dumps(payload),
                properties=pika.BasicProperties(
                    delivery_mode=pika.DeliveryMode.Persistent
                )
            )
            logging.info(f"Sent Job ID : {payload['job_id']} to queue.")
        except Exception as e:
            logging.error(f"Producer: Failed to send job ID {job_id} to queue: {e}")
            raise
        finally:
            self.close_connection()

    def close_connection(self) -> None:
        try:
            self.connection.close()
            logging.debug("Producer: Connection closed.")
        except Exception as e:
            logging.warning(f"Producer: Error while closing connection: {e}")