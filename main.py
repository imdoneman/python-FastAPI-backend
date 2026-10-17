
from contextlib import asynccontextmanager
from time import time
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import models
from database import engine, get_db
from schemas import TeaCreate, TeaResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)
start_time = time()


@app.get("/")
def read_root():
    return {"message": "welcome to the tea house"}


@app.get("/pulse")
def pulse():
    return {
        "status": "online",
        "uptime": f"{int(time() - start_time)}s",
        "version": "2.1.0",
    }


@app.get("/teas", response_model=List[TeaResponse])
def list_teas(db: Session = Depends(get_db)):
    return db.query(models.TeaItem).all()


@app.post("/teas", status_code=status.HTTP_201_CREATED)
def create_tea(tea: TeaCreate, db: Session = Depends(get_db)):
    existing_tea = (
        db.query(models.TeaItem)
        .filter(models.TeaItem.name == tea.name)
        .first()
    )

    if existing_tea:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tea name '{tea.name}' already exists.",
        )

    db_tea = models.TeaItem(**tea.model_dump())
    db.add(db_tea)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tea name '{tea.name}' already exists.",
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tea creation failed. No tea was inserted.",
        )

    return {"inserted": 1}


@app.post("/teas/bulk")
def create_teas(
    tea_inputs: List[TeaCreate],
    response: Response,
    db: Session = Depends(get_db),
):
    if not tea_inputs:
        return {
            "inserted": 0,
            "message": "No teas were submitted; nothing was inserted.",
        }

    names = [tea.name for tea in tea_inputs]
    seen_names = set()
    repeated_names = set()

    for name in names:
        if name in seen_names:
            repeated_names.add(name)
        seen_names.add(name)

    if repeated_names:
        repeated_name = sorted(repeated_names)[0]
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Bulk insertion aborted. No teas were inserted.",
                "reason": (
                    f"Tea name '{repeated_name}' appears more than once "
                    "in this batch."
                ),
            },
        )

    existing_teas = (
        db.query(models.TeaItem)
        .filter(models.TeaItem.name.in_(names))
        .all()
    )

    if existing_teas:
        existing_name = existing_teas[0].name
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Bulk insertion aborted. No teas were inserted.",
                "reason": f"Tea name '{existing_name}' already exists.",
            },
        )

    db.add_all(
        models.TeaItem(**tea.model_dump())
        for tea in tea_inputs
    )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": "Bulk insertion aborted. No teas were inserted.",
                "reason": (
                    "A tea name conflicts with an existing record. "
                    "Please refresh the inventory and retry."
                ),
            },
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bulk insertion failed. No teas were inserted.",
        )

    response.status_code = status.HTTP_201_CREATED
    return {"inserted": len(tea_inputs)}


@app.put("/teas/{tea_id}", response_model=TeaResponse)
def update_tea(
    tea_id: int,
    updated_tea: TeaCreate,
    db: Session = Depends(get_db),
):
    db_tea = (
        db.query(models.TeaItem)
        .filter(models.TeaItem.id == tea_id)
        .first()
    )

    if not db_tea:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tea with ID {tea_id} not found.",
        )

    conflicting_tea = (
        db.query(models.TeaItem)
        .filter(
            models.TeaItem.name == updated_tea.name,
            models.TeaItem.id != tea_id,
        )
        .first()
    )

    if conflicting_tea:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tea name '{updated_tea.name}' already exists.",
        )

    db_tea.name = updated_tea.name
    db_tea.origin = updated_tea.origin

    try:
        db.commit()
        db.refresh(db_tea)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tea name '{updated_tea.name}' already exists.",
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tea update failed.",
        )

    return db_tea


@app.delete("/teas/{tea_id}")
def delete_tea(tea_id: int, db: Session = Depends(get_db)):
    db_tea = (
        db.query(models.TeaItem)
        .filter(models.TeaItem.id == tea_id)
        .first()
    )

    if not db_tea:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tea with ID {tea_id} not found.",
        )

    db.delete(db_tea)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tea deletion failed.",
        )

    return {"message": f"Successfully deleted tea item with ID {tea_id}"}
