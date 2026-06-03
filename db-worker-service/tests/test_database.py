import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch

from worker import app
from database import get_db, Base
import models

# 1. Setup a volatile, in-memory database specifically for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 2. Dependency Override: Hijack the FastAPI route to use our test DB
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# 3. Block the RabbitMQ consumer thread from booting during tests
@pytest.fixture(autouse=True)
def mock_rabbitmq_thread():
    # Instead of patching the Thread object, we patch the function itself
    with patch("worker.start_rabbitmq_consumer"):
        yield

        
# 4. Build and tear down the database tables for every single test
@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# --- THE TESTS ---

client = TestClient(app)

def test_worker_pulse():
    response = client.get("/pulse")
    assert response.status_code == 200
    assert response.json()["status"] == "worker_online"

def test_internal_get_teas_empty():
    """Ensure the internal route returns an empty list on a fresh database."""
    response = client.get("/internal/teas")
    assert response.status_code == 200
    assert response.json() == []

def test_internal_get_teas_with_data():
    """Manually insert data using SQLAlchemy, then test if the web route can fetch it."""
    # Seed the database
    db = TestingSessionLocal()
    test_tea = models.TeaItem(name="Earl Grey Test", origin="UK")
    db.add(test_tea)
    db.commit()
    db.close()

    # Hit the API route
    response = client.get("/internal/teas")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Earl Grey Test"