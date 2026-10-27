import json
import os

import pika


QUEUE_NAME = "tea_tasks"


class RabbitMQPublishError(RuntimeError):
    """Raised when a command cannot be confirmed by RabbitMQ."""


def _connection_parameters():
    rabbitmq_url = os.getenv("RABBITMQ_URL")

    if rabbitmq_url:
        return pika.URLParameters(rabbitmq_url)

    return pika.ConnectionParameters(
        host=os.getenv("RABBITMQ_HOST", "localhost"),
        connection_attempts=3,
        retry_delay=2,
        socket_timeout=5,
        blocked_connection_timeout=10,
        heartbeat=30,
    )


def publish_to_queue(action: str, payload: dict | list) -> None:
    """Publish a persistent command and require a broker confirmation."""
    connection = None

    message = {
        "action": action,
        "data": payload,
    }

    try:
        connection = pika.BlockingConnection(
            _connection_parameters()
        )

        channel = connection.channel()
        channel.queue_declare(
            queue=QUEUE_NAME,
            durable=True,
        )
        channel.confirm_delivery()

        confirmed = channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,
                content_type="application/json",
            ),
            mandatory=True,
        )

        if confirmed is False:
            raise RabbitMQPublishError(
                "RabbitMQ did not confirm the published message."
            )

    except RabbitMQPublishError:
        raise

    except Exception as exc:
        raise RabbitMQPublishError(
            f"Failed to publish '{action}' command."
        ) from exc

    finally:
        if connection is not None and connection.is_open:
            connection.close()