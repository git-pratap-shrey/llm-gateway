import json
import pika
from router import Router
from result_store import result_store

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

        payload = json.loads(body.decode())
        payload["response"] = Router().route(payload["data"])
        payload["status"] = "completed"

        print(f"Processed: {payload}")
        result_store.add_to_database(payload)
        
        ch.basic_ack(delivery_tag=method.delivery_tag)


    def close_connection(self):
        self.connection.close()