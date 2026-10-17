
from time import time
from typing import List

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel


app = FastAPI()

start_time = time()
next_tea_id = 1


class TeaInput(BaseModel):
    name: str
    origin: str


class Tea(TeaInput):
    id: int


teas: List[Tea] = []


def create_tea(tea_input: TeaInput) -> None:
    """Add a tea using the next available ID."""
    global next_tea_id

    tea = Tea(
        id=next_tea_id,
        name=tea_input.name,
        origin=tea_input.origin,
    )
    teas.append(tea)
    next_tea_id += 1


@app.get("/")
def read_root():
    return {"message": "welcome to the tea house"}


@app.get("/pulse")
def pulse():
    return {
        "status": "online",
        "uptime": f"{int(time() - start_time)}s",
        "version": "1.1.0",
    }


@app.get("/teas", response_model=List[Tea])
def home_teas():
    return teas


@app.post("/teas", status_code=201)
def add_tea(tea: TeaInput):
    create_tea(tea)
    return {"inserted": 1}


@app.post("/teas/bulk")
def add_multiple_teas(
    multiple_teas: List[TeaInput],
    response: Response,
):
    inserted_count = len(multiple_teas)

    if inserted_count == 0:
        response.status_code = 200
        return {"inserted": 0}

    # FastAPI validates the entire request body before this function runs.
    # Therefore, invalid input cannot cause a partially inserted batch.
    for tea in multiple_teas:
        create_tea(tea)

    response.status_code = 201
    return {"inserted": inserted_count}


@app.put("/teas/{tea_id}", response_model=List[Tea])
def update_tea(tea_id: int, updated_tea: TeaInput):
    for index, tea in enumerate(teas):
        if tea.id == tea_id:
            teas[index] = Tea(
                id=tea_id,
                name=updated_tea.name,
                origin=updated_tea.origin,
            )
            return teas

    raise HTTPException(
        status_code=404,
        detail=f"Tea with ID {tea_id} not found",
    )


@app.delete("/teas/{tea_id}", response_model=List[Tea])
def delete_tea(tea_id: int):
    for index, tea in enumerate(teas):
        if tea.id == tea_id:
            teas.pop(index)
            return teas

    raise HTTPException(
        status_code=404,
        detail=f"Tea with ID {tea_id} not found",
    )
