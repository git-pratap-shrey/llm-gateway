import logging
import json
import pika
from typing import Any
from router import Router
from result_store.result_store import Result_store
    
class Consumer:
    def __init__(self) -> None:
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host="localhost")
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
        logging.info(f"Received job ID {payload['job_id']} for processing.")

        payload["output"] = Router().route(payload["input"])

        payload["status"] = "completed"

        logging.info(f"Processed job ID {payload['job_id']}")
        
        Result_store().add_to_database(payload)
        
        ch.basic_ack(delivery_tag=method.delivery_tag)


    def close_connection(self) -> None:
        self.connection.close()