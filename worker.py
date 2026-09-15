from message_queue.producer import Producer
from message_queue.consumer import Consumer

class Worker:
    def produce_message(self, payload):
        self.producer = Producer()
        self.producer.send_message(payload)

    def consume_message(self):
        self.consumer = Consumer()
        self.consumer.start_consuming()

if __name__ == "__main__":
    worker = Worker()
    worker.consume_message()