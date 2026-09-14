from message_queue.producer import Producer
from message_queue.consumer import Consumer

class Worker:
    def produce_message(self, message):
        self.producer = Producer()
        self.producer.send_message(message)

        self.close_connection()

    def consume_message(self):
        self.consumer = Consumer()
        self.consumer.start_consuming()

        self.close_connection()

if __name__ == "__main__":
    worker = Worker()
    worker.consume_message()