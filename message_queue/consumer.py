import json
import pika
from router import router

class Consumer:
    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host="localhost")
        )
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue="tasks", durable=True)

    def start_consuming(self):
        self.channel.basic_consume(
            queue="tasks",
            on_message_callback=self.callback
        )

        print("Waiting for messages...")
        self.channel.start_consuming()

    def callback(self, ch, method, properties, body):
        print(f"Received: {body.decode()}")

        router().route(json.loads(body.decode()))

        ch.basic_ack(delivery_tag=method.delivery_tag)

    def close_connection(self):
        self.connection.close()