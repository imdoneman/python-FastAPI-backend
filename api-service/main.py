import time
import httpx2
from fastapi import FastAPI, HTTPException, status
from typing import List

# 💡 Notice what is missing: Zero database imports. No SQLAlchemy. No engine.
from schemas import TeaCreate, TeaResponse
from producer import publish_to_queue

app = FastAPI(openapi_url="/openapi.json", docs_url="/docs", redoc_url="/redoc")

start_time = time.time()

# 💡 Internal DNS for the Kubernetes Service that actually touches the database
INTERNAL_DB_SERVICE_URL = "http://db-worker-service:8080"


# =====================================================================
# SYSTEM ROUTES
# =====================================================================

@app.get("/")
def read_root():
    return {"message": "welcome to the distributed tea house"}


@app.get("/pulse")
def pulse():
    return {
        "status": "online",
        "uptime": f"{int(time.time() - start_time)}s",
        "version": "3.1.0" # Version bump for the pure microservice transition
    }


# =====================================================================
# QUERIES (Reads): Fetched over the network from the DB Worker
# =====================================================================

@app.get("/teas", response_model=List[TeaResponse])
async def home_teas():
    # The API no longer touches the database! It asks the worker service for the data.
    async with httpx2.AsyncClient() as client:
        try:
            response = await client.get(f"{INTERNAL_DB_SERVICE_URL}/internal/teas")
            response.raise_for_status()
            return response.json()
        except httpx2.RequestError:
            # If the DB worker is offline, we handle the network failure gracefully
            raise HTTPException(
                status_code=503, 
                detail="Database service is currently unreachable."
            )


# =====================================================================
# COMMANDS (Writes): Handed off to RabbitMQ (CQRS Pattern)
# =====================================================================

@app.post("/teas", status_code=status.HTTP_202_ACCEPTED)
def add_teas(tea: TeaCreate):
    # We no longer check for duplicates here. The DB Worker handles that logic.
    publish_to_queue(action="create", payload=tea.model_dump())
    
    # We return 202 Accepted because the item isn't created yet, just queued.
    return {"status": "Accepted", "message": f"Creation task for '{tea.name}' queued successfully."}


@app.post("/teas/bulk", status_code=status.HTTP_202_ACCEPTED)
def add_multiple_teas(multiple_teas: List[TeaCreate]):
    # Serialize the list of Pydantic models into native dictionaries
    serialized_teas = [tea.model_dump() for tea in multiple_teas]
    publish_to_queue(action="bulk_create", payload=serialized_teas)
    
    return {"status": "Accepted", "message": f"Bulk creation task for {len(serialized_teas)} items queued."}


@app.put("/teas/{tea_id}", status_code=status.HTTP_202_ACCEPTED)
def update_teas(tea_id: int, updated_tea: TeaCreate):
    payload = {
        "id": tea_id,
        "update_data": updated_tea.model_dump()
    }
    publish_to_queue(action="update", payload=payload)
    
    return {"status": "Accepted", "message": f"Update task for Tea ID {tea_id} queued."}


@app.delete("/teas/{tea_id}", status_code=status.HTTP_202_ACCEPTED)
def delete_teas(tea_id: int):
    publish_to_queue(action="delete", payload={"id": tea_id})
    return {"status": "Accepted", "message": f"Deletion task for Tea ID {tea_id} queued."}