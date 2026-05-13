from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import time

app = FastAPI()


class Tea(BaseModel):
    id: int
    name: str
    origin: str


teas: List[Tea] = []
start_time = time.time()


@app.get("/")
def read_root():
    return {"message": "welcome to the tea house"}


@app.get("/pulse")
def pulse():
    return {
        "status": "online",
        "uptime": f"{int(time.time() - start_time)}s",
        "version": "1.0.0"
    }


@app.get("/teas")
def home_teas():
    return teas


@app.post("/teas")
def add_teas(tea: Tea):
    teas.append(tea)
    return teas


@app.post("/teas/bulk")
def add_multiple_teas(multiple_teas: List[Tea]):
    try:
        teas.extend(multiple_teas)
        return {"message": f"Added {len(teas)} teas!"}
    except Exception as e:
        return {"error": "Something went wrong!", "details": str(e)}


@app.put("/teas/{tea_id}")
def update_teas(tea_id: int, updated_tea: Tea):
    for index, tea in enumerate(teas):
        if tea.id == tea_id:
            teas[index] = updated_tea
            return teas
    return {"error": "no record found"}


@app.delete("/teas/{tea_id}")
def delete_teas(tea_id: int):
    for index, tea in enumerate(teas):
        if tea.id == tea_id:
            teas.pop(index)
            return teas
    return "no record found"
