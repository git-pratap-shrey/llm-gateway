import logging
import pika
from fastapi import HTTPException
from message_queue.producer import Producer
from message_queue.consumer import Consumer
from typing import Any

class Worker:
    def produce_message(self, payload: dict[str, Any]) -> None:
        try:
            self.producer = Producer()
            self.producer.send_message(payload)

        except pika.exceptions.AMQPConnectionError as e:
            logging.debug(f"RabbitMQ connection failed while producing message: {e}")
            raise HTTPException(503, 
                                detail={"job_id": None, 
                                        "message": "rabbitmq client not available"}) 
        # ponytail: 503 lets FastAPI handle the response — no catch needed in main.py

    def consume_message(self) -> None:
        self.consumer = Consumer()
        self.consumer.start_consuming()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        Worker().consume_message()
    except pika.exceptions.AMQPConnectionError as e:
        logging.error(f"RabbitMQ connection failed: {e}")
