import pika
import json

class Producer:
    def __init__(self):
        self.connection = pika.BlockingConnection(
            pika.ConnectionParameters(host="localhost")
        )
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue="tasks", durable=True)

    def send_message(self, message: dict):
        self.channel.basic_publish(
            exchange="",
            routing_key="tasks",
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent
            )
        )
        
        print(f"Sent: {message}")

        self.close_connection()

    def close_connection(self):
        self.connection.close()