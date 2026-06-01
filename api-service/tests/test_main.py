import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
# 👈 CRITICAL: Needed to share memory across threads
from sqlalchemy.pool import StaticPool

# 1. Import modules to bind references
import main
from main import app
import models
from database import Base

# 2. Configure the Engine with a Static Pool
# This keeps the in-memory tables alive and accessible across all internal connections
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool  # 👈 FORCE sharing the same memory connection slot
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# 3. Direct explicit override linkage
app.dependency_overrides[main.get_db] = override_get_db

client = TestClient(app)

# 4. Synchronized Lifecycle Fixture


@pytest.fixture(autouse=True)
def setup_database():
    # Because of StaticPool, this builds tables in the EXACT space FastAPI reads from
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

# =====================================================================
# SYNCHRONIZED TEST CASES
# =====================================================================


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "welcome to the tea house"}


def test_pulse():
    response = client.get("/pulse")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_add_and_get_tea():
    # Payload matches schemas.TeaCreate (no ID field passed)
    new_tea = {"name": "Darjeeling First Flush",
               "origin": "West Bengal, India"}

    # Test POST (Expects 201 Created from main.py)
    post_response = client.post("/teas", json=new_tea)
    assert post_response.status_code == 201
    assert post_response.json()["id"] == 1

    # Test GET
    get_response = client.get("/teas")
    assert get_response.status_code == 200
    assert len(get_response.json()) == 1
    assert get_response.json()[0]["name"] == "Darjeeling First Flush"


def test_delete_tea():
    # Insert a temporary item to target
    post_res = client.post(
        "/teas", json={"name": "Assam Black", "origin": "Assam, India"})
    tea_id = post_res.json()["id"]

    # Execute DELETE target payload route
    response = client.delete(f"/teas/{tea_id}")
    assert response.status_code == 200

    # Confirm database inventory is completely clear
    get_response = client.get("/teas")
    assert len(get_response.json()) == 0
