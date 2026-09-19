import logging
import pika
import json
from typing import Any

class Producer:
    def __init__(self) -> None:
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host="localhost")
        )
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue="tasks", durable=True)

    def send_message(self, payload: dict[str, Any]) -> None:
        self.channel.basic_publish(
            exchange="",
            routing_key="tasks",
            body=json.dumps(payload),
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent
            )
        )
        
        logging.info(f"Sent Job ID : {payload['job_id']} to queue.")

        self.close_connection()

    def close_connection(self) -> None:
        self.connection.close()