from fastapi import FastAPI, Depends, HTTPException, status
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import List
import time
from sqlalchemy.orm import Session

# Import our database infrastructure components
import models
from schemas import TeaCreate, TeaResponse
from database import engine, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs on web server startup (production/dev mode)
    models.Base.metadata.create_all(bind=engine)
    yield
    # Clean up on shutdown if needed

app = FastAPI(lifespan=lifespan)

# # On boot, look at models.py and build any tables that do not exist yet
# models.Base.metadata.create_all(bind=engine)


start_time = time.time()


# class Tea(BaseModel):
#     id: int
#     name: str
#     origin: str


# teas: List[Tea] = []


# =====================================================================
# API ENDPOINTS (The Monolith CRUD Routes)
# =====================================================================

@app.get("/")
def read_root():
    return {"message": "welcome to the tea house"}


@app.get("/pulse")
def pulse():
    return {
        "status": "online",
        "uptime": f"{int(time.time() - start_time)}s",
        "version": "1.0.4"
    }


@app.get("/teas", response_model=List[TeaResponse])
def home_teas(db: Session = Depends(get_db)):
    # Query all records from the 'teas' table
    return db.query(models.TeaItem).all()


@app.post("/teas", response_model=TeaResponse, status_code=status.HTTP_201_CREATED)
def add_teas(tea: TeaCreate, db: Session = Depends(get_db)):

    existing_tea = db.query(models.TeaItem).filter(
        # Enforce uniqueness constraint check manually for clean API error returns
        models.TeaItem.name == tea.name).first()

    if existing_tea:
        raise HTTPException(
            status_code=400, detail="This tea variety already exist in inventory.")

    db_tea = models.TeaItem(**tea.model_dump())
    db.add(db_tea)
    db.commit()
    db.refresh(db_tea)
    return db_tea


@app.post("/teas/bulk")
def add_multiple_teas(multiple_teas: List[TeaCreate], db: Session = Depends(get_db)):
    try:
        inserted_count = 0
        for tea_data in multiple_teas:
            # Check for duplicates inline during bulk processing
            if not db.query(models.TeaItem).filter(models.TeaItem.name == tea_data.name).first():
                db_tea = models.TeaItem(**tea_data.model_dump())
                db.add(db_tea)
                inserted_count += 1
        db.commit()
        return {"message": f"Successfully processed Items! add {inserted_count} fresh entries."}
    except Exception as e:
        db.rollback()  # Safely abort transaction if structure errors happen
        raise HTTPException(status_code=500, detail={
                            "error": "bulk insertion failed", "details": str(e)})


@app.put("/teas/{tea_id}", response_model=TeaResponse)
def update_teas(tea_id: int, updated_tea: TeaCreate, db: Session = Depends(get_db)):
    db_tea = db.query(models.TeaItem).filter(
        models.TeaItem.id == tea_id).first()
    if not db_tea:
        raise HTTPException(
            status_code=404, detail="No record found with that ID.")

    # Update object values directly
    db_tea.name = updated_tea.name
    db_tea.origin = updated_tea.origin

    db.commit()
    db.refresh(db_tea)
    return db_tea


@app.delete("/teas/{tea_id}")
def delete_teas(tea_id: int, db: Session = Depends(get_db)):
    db_tea = db.query(models.TeaItem).filter(
        models.TeaItem.id == tea_id).first()
    if not db_tea:
        raise HTTPException(
            status_code=404, detail="No record found with that ID.")
    db.delete(db_tea)
    db.commit()
    return {"message": f"Successfully deleted tea item with ID {tea_id}"}
