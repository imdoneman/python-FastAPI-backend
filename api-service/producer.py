import pika
import json
import os

# Fetch the broker URL from the environment, defaulting to localhost for local dev
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
QUEUE_NAME = "tea_tasks"

def publish_to_queue(action: str, payload: dict | list):
    """
    Pushes a task to RabbitMQ to be asynchronously consumed by the DB Worker.
    """
    try:
        # Establish a synchronous connection to the RabbitMQ server
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST)
        )
        channel = connection.channel()

        # Idempotent queue declaration (creates it if it doesn't exist)
        # durable=True ensures the queue survives a RabbitMQ server crash
        channel.queue_declare(queue=QUEUE_NAME, durable=True)

        # Structure the message exactly how the worker expects to read it
        message = {
            "action": action,
            "data": payload
        }

        # Publish the payload
        channel.basic_publish(
            exchange='',
            routing_key=QUEUE_NAME,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # 2 makes the message persistent on disk
            )
        )
        
        print(f"[*] Successfully queued '{action}' task.")
        
    except Exception as e:
        # In a strict production setup, you would log this to Datadog/CloudWatch
        print(f"[!] Failed to publish message to RabbitMQ: {e}")
        
    finally:
        # Always close the connection to prevent memory leaks
        if 'connection' in locals() and connection.is_open:
            connection.close()