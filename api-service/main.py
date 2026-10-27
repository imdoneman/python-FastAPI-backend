
import time
from typing import Annotated

import httpx2
from fastapi import FastAPI, HTTPException, Path, status
from prometheus_fastapi_instrumentator import Instrumentator

from producer import RabbitMQPublishError, publish_to_queue
from schemas import TeaCreate, TeaResponse


app = FastAPI(
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

Instrumentator(excluded_handlers=["/metrics"]).instrument(app).expose(app, include_in_schema=False)

start_time = time.time()

INTERNAL_DB_SERVICE_URL = "http://db-worker-service:8080"
WORKER_REQUEST_TIMEOUT = 5.0


@app.get("/")
def read_root():
    return {"message": "welcome to the distributed tea house"}


@app.get("/pulse")
def pulse():
    return {
        "status": "online",
        "uptime": f"{int(time.time() - start_time)}s",
        "version": "3.1.0",
    }


@app.get("/teas", response_model=list[TeaResponse])
async def home_teas():
    try:
        async with httpx2.AsyncClient(
            timeout=WORKER_REQUEST_TIMEOUT
        ) as client:
            response = await client.get(
                f"{INTERNAL_DB_SERVICE_URL}/internal/teas"
            )
            response.raise_for_status()
            return response.json()

    except httpx2.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Database service request timed out.",
        )

    except httpx2.HTTPStatusError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Database service returned an unsuccessful response.",
        )

    except httpx2.RequestError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service is currently unreachable.",
        )


def publish_command(action: str, payload: dict | list) -> None:
    """Publish a command or return an HTTP error if publishing fails."""
    try:
        publish_to_queue(action=action, payload=payload)
    except RabbitMQPublishError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Message broker is currently unavailable. Please retry.",
        )


@app.post("/teas", status_code=status.HTTP_202_ACCEPTED)
def add_teas(tea: TeaCreate):
    publish_command("create", tea.model_dump())

    return {
        "status": "Accepted",
        "message": f"Creation task for '{tea.name}' queued successfully.",
    }


@app.post("/teas/bulk", status_code=status.HTTP_202_ACCEPTED)
def add_multiple_teas(multiple_teas: list[TeaCreate]):
    if not multiple_teas:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one tea must be provided.",
        )

    serialized_teas = [
        tea.model_dump() for tea in multiple_teas
    ]

    publish_command("bulk_create", serialized_teas)

    return {
        "status": "Accepted",
        "message": (
            f"Bulk creation task for {len(serialized_teas)} items queued."
        ),
    }


@app.put("/teas/{tea_id}", status_code=status.HTTP_202_ACCEPTED)
def update_teas(
    tea_id: Annotated[int, Path(gt=0)],
    updated_tea: TeaCreate,
):
    payload = {
        "id": tea_id,
        "update_data": updated_tea.model_dump(),
    }

    publish_command("update", payload)

    return {
        "status": "Accepted",
        "message": f"Update task for Tea ID {tea_id} queued.",
    }


@app.delete("/teas/{tea_id}", status_code=status.HTTP_202_ACCEPTED)
def delete_teas(tea_id: Annotated[int, Path(gt=0)]):
    publish_command("delete", {"id": tea_id})

    return {
        "status": "Accepted",
        "message": f"Deletion task for Tea ID {tea_id} queued.",
    }
