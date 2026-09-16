from message_queue.producer import Producer
from message_queue.consumer import Consumer
from typing import Any

class Worker:
    def produce_message(self, payload: dict[str, Any]) -> None:
        self.producer = Producer()
        self.producer.send_message(payload)

    def consume_message(self) -> None:
        self.consumer = Consumer()
        self.consumer.start_consuming()

if __name__ == "__main__":
    worker = Worker()
    worker.consume_message()