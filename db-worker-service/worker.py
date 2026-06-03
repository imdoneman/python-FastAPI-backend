import os
import json
import time
import threading
import pika
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session

# Import your DB infrastructure (This service OWNS the database)
import models
from database import engine, get_db, SessionLocal

# Ensure tables exist on boot
# models.Base.metadata.create_all(bind=engine)

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_QUEUE = "tea_tasks"

# =====================================================================
# BACKGROUND TASK: RabbitMQ Consumer Logic
# =====================================================================

def process_task(ch, method, properties, body):
    """Executes when a message arrives in the queue."""
    payload = json.loads(body)
    action = payload.get("action")
    data = payload.get("data")
    
    print(f"[*] Worker received task: {action}")
    
    # Open a fresh DB session for each message
    db: Session = SessionLocal()
    
    try:
        if action == "create":
            db_tea = models.TeaItem(**data)
            db.add(db_tea)
            db.commit()
            print(f"    [+] Created: {db_tea.name}")
            
        elif action == "bulk_create":
            for tea_data in data:
                if not db.query(models.TeaItem).filter(models.TeaItem.name == tea_data["name"]).first():
                    db.add(models.TeaItem(**tea_data))
            db.commit()
            print("    [+] Bulk insert complete.")

        elif action == "update":
            db_tea = db.query(models.TeaItem).filter(models.TeaItem.id == data["id"]).first()
            if db_tea:
                db_tea.name = data["update_data"]["name"]
                db_tea.origin = data["update_data"]["origin"]
                db.commit()
                print(f"    [+] Updated Tea ID: {data['id']}")

        elif action == "delete":
            db_tea = db.query(models.TeaItem).filter(models.TeaItem.id == data["id"]).first()
            if db_tea:
                db.delete(db_tea)
                db.commit()
                print(f"    [-] Deleted Tea ID: {data['id']}")
                
    except Exception as e:
        print(f"    [X] Database Error: {e}")
        db.rollback()
    finally:
        db.close()
        # Acknowledge completion so RabbitMQ removes it from the queue
        ch.basic_ack(delivery_tag=method.delivery_tag)

def start_rabbitmq_consumer():
    """Connects to RabbitMQ and starts the blocking consumer loop."""
    print(f"[*] Booting background consumer connected to {RABBITMQ_HOST}...")
    
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
            break
        except pika.exceptions.AMQPConnectionError:
            print("[!] RabbitMQ not ready. Retrying in 5s...")
            time.sleep(5)

    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE, durable=True)
    
    # prefetch_count=1 ensures RabbitMQ only gives one message to this worker at a time, 
    # preventing memory overload if there's a massive traffic spike
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=process_task)
    
    print(' [*] Background Consumer is online.')
    channel.start_consuming()


# =====================================================================
# MAIN THREAD: Internal Web Server (Lifespan + Routes)
# =====================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Attempt to build tables on boot, but catch the error if the DB is offline (or if we are testing)
    try:
        models.Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[!] Warning: Could not connect to real database on boot: {e}")

    # 2. Spawn the RabbitMQ consumer
    consumer_thread = threading.Thread(target=start_rabbitmq_consumer, daemon=True)
    consumer_thread.start()
    yield

# Notice we disable docs because this is an internal service, not public-facing!
app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

@app.get("/pulse")
def pulse():
    return {"status": "worker_online"}

@app.get("/internal/teas")
def internal_get_teas(db: Session = Depends(get_db)):
    """
    This route ONLY exists to serve the api-service. 
    It fetches the data directly from Postgres.
    """
    return db.query(models.TeaItem).all() 