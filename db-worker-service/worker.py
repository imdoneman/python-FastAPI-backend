import json
import os
import threading
import time
from contextlib import asynccontextmanager

import pika
from fastapi import Depends, FastAPI
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import models
from database import engine, get_db, SessionLocal


RABBITMQ_QUEUE = "tea_tasks"


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


def process_task(ch, method, properties, body):
    """Process a RabbitMQ command and acknowledge only successful work."""
    try:
        message = json.loads(body)
        if not isinstance(message, dict):
            raise ValueError("Message must be a JSON object.")

        action = message.get("action")
        data = message.get("data")

        if action not in {"create", "bulk_create", "update", "delete"}:
            raise ValueError("Unsupported message action.")

        if not isinstance(data, (dict, list)):
            raise ValueError("Message data must be an object or list.")

        if action == "bulk_create" and not isinstance(data, list):
            raise ValueError("bulk_create requires a list.")

        if action != "bulk_create" and not isinstance(data, dict):
            raise ValueError(f"{action} requires an object.")

    except (json.JSONDecodeError, UnicodeDecodeError, ValueError, TypeError):
        print("[!] Rejecting malformed or unsupported message.")
        ch.basic_reject(
            delivery_tag=method.delivery_tag,
            requeue=False,
        )
        return

    db: Session = SessionLocal()

    try:
        if action == "create":
            existing = (
                db.query(models.TeaItem)
                .filter(models.TeaItem.name == data["name"])
                .first()
            )

            # Duplicate delivery is treated as already completed.
            if existing is None:
                db.add(models.TeaItem(**data))
                db.commit()

            print(f"    [+] Create processed: {data['name']}")

        elif action == "bulk_create":
            for tea_data in data:
                if not isinstance(tea_data, dict):
                    raise ValueError("Each bulk item must be an object.")

                existing = (
                    db.query(models.TeaItem)
                    .filter(
                        models.TeaItem.name == tea_data["name"]
                    )
                    .first()
                )

                if existing is None:
                    db.add(models.TeaItem(**tea_data))

            db.commit()
            print("    [+] Bulk insert processed.")

        elif action == "update":
            tea_id = data["id"]
            update_data = data["update_data"]

            if not isinstance(update_data, dict):
                raise ValueError("update_data must be an object.")

            db_tea = (
                db.query(models.TeaItem)
                .filter(models.TeaItem.id == tea_id)
                .first()
            )

            if db_tea:
                db_tea.name = update_data["name"]
                db_tea.origin = update_data["origin"]
                db.commit()

            print(f"    [+] Update processed for Tea ID: {tea_id}")

        elif action == "delete":
            tea_id = data["id"]

            db_tea = (
                db.query(models.TeaItem)
                .filter(models.TeaItem.id == tea_id)
                .first()
            )

            if db_tea:
                db.delete(db_tea)
                db.commit()

            print(f"    [-] Delete processed for Tea ID: {tea_id}")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except (KeyError, TypeError, ValueError):
        db.rollback()
        print("[!] Rejecting command with invalid data.")
        ch.basic_reject(
            delivery_tag=method.delivery_tag,
            requeue=False,
        )

    except SQLAlchemyError as exc:
        db.rollback()
        print(f"[!] Database operation failed; requeueing message: {exc}")
        ch.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=True,
        )

    except Exception as exc:
        db.rollback()
        print(f"[!] Unexpected processing failure; requeueing message: {exc}")
        ch.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=True,
        )

    finally:
        db.close()


def start_rabbitmq_consumer():
    """Reconnect when RabbitMQ is unavailable or a connection is lost."""
    while True:
        connection = None

        try:
            print("[*] Connecting worker to RabbitMQ...")
            connection = pika.BlockingConnection(
                _connection_parameters()
            )

            channel = connection.channel()
            channel.queue_declare(
                queue=RABBITMQ_QUEUE,
                durable=True,
            )
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(
                queue=RABBITMQ_QUEUE,
                on_message_callback=process_task,
            )

            print("[*] RabbitMQ consumer is online.")
            channel.start_consuming()

        except pika.exceptions.AMQPConnectionError as exc:
            print(f"[!] RabbitMQ connection failed: {exc}")

        except Exception as exc:
            print(f"[!] Consumer stopped unexpectedly: {exc}")

        finally:
            if connection is not None and connection.is_open:
                connection.close()

        time.sleep(5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail startup rather than reporting a healthy worker with no DB access.
    models.Base.metadata.create_all(bind=engine)

    consumer_thread = threading.Thread(
        target=start_rabbitmq_consumer,
        daemon=True,
    )
    consumer_thread.start()

    yield


app = FastAPI(
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.get("/pulse")
def pulse():
    return {"status": "worker_online"}


@app.get("/internal/teas")
def internal_get_teas(db: Session = Depends(get_db)):
    teas = db.query(models.TeaItem).all()

    return [
        {
            "id": tea.id,
            "name": tea.name,
            "origin": tea.origin,
        }
        for tea in teas
    ]