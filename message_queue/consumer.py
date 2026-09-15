import json
import pika
from router import router
from result_store import add_to_database

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

        body["response"] = router().route(body["data"])
        body["status"] = "completed"

        add_to_database(body)

        ch.basic_ack(delivery_tag=method.delivery_tag)


    def close_connection(self):
        self.connection.close()