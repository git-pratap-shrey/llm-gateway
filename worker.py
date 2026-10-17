import logging
import pika
from fastapi import HTTPException
from message_queue.producer import Producer
from message_queue.consumer import Consumer
from typing import Any

class Worker:
    def produce_message(self, payload: dict[str, Any]) -> None:
        job_id = payload.get("job_id", "unknown")
        try:
            logging.info(f"Worker: Producing message for job ID: {job_id}.")
            self.producer = Producer()
            self.producer.send_message(payload)
            logging.info(f"Worker: Successfully produced message for job ID: {job_id}.")

        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"RabbitMQ connection failed while producing message: {e}")
            raise HTTPException(503, 
                                detail={"job_id": None, 
                                        "message": "rabbitmq client not available"}) 
        # ponytail: 503 lets FastAPI handle the response — no catch needed in main.py

    def consume_message(self) -> None:
        logging.info("Worker: Starting message consumption...")
        self.consumer = Consumer()
        self.consumer.start_consuming()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logging.info("Worker process starting...")
    try:
        Worker().consume_message()
    except KeyboardInterrupt:
        logging.info("Worker process stopped by user.")
    except pika.exceptions.AMQPConnectionError as e:
        logging.error(f"RabbitMQ connection failed: {e}")
    except Exception as e:
        logging.error(f"Worker process encountered unhandled error: {e}")
