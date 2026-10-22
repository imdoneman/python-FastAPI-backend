
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
import models
from database import Base


TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


main.app.dependency_overrides[main.get_db] = override_get_db
client = TestClient(main.app)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def tea_payload(name="Darjeeling First Flush",
                origin="West Bengal, India"):
    return {"name": name, "origin": origin}


def test_read_root():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "welcome to the tea house"}


def test_pulse():
    response = client.get("/pulse")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["uptime"].endswith("s")
    assert data["version"] == "2.3.0"


def test_get_teas_initially_returns_empty_list():
    response = client.get("/teas")

    assert response.status_code == 200
    assert response.json() == []


def test_create_tea_returns_count_and_get_returns_generated_id():
    response = client.post("/teas", json=tea_payload())

    assert response.status_code == 201
    assert response.json() == {"inserted": 1}

    teas = client.get("/teas").json()
    assert len(teas) == 1
    assert teas[0] == {
        "id": 1,
        "name": "Darjeeling First Flush",
        "origin": "West Bengal, India",
    }


def test_create_multiple_teas_generates_unique_ids():
    first = client.post("/teas", json=tea_payload("Darjeeling", "India"))
    second = client.post("/teas", json=tea_payload("Assam", "India"))

    assert first.json() == {"inserted": 1}
    assert second.json() == {"inserted": 1}
    assert [tea["id"] for tea in client.get("/teas").json()] == [1, 2]


def test_create_duplicate_name_returns_conflict():
    client.post("/teas", json=tea_payload("Assam Black", "Assam"))

    response = client.post("/teas", json=tea_payload("Assam Black", "India"))

    assert response.status_code == 409
    assert client.get("/teas").json() == [
        {"id": 1, "name": "Assam Black", "origin": "Assam"}
    ]


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "origin": "India"},
        {"name": "Darjeeling"},
        {"name": "x" * 51, "origin": "India"},
        {"name": "Darjeeling", "origin": "x" * 101},
    ],
)
def test_invalid_tea_payload_returns_422(payload):
    response = client.post("/teas", json=payload)

    assert response.status_code == 422
    assert client.get("/teas").json() == []


def test_bulk_create_returns_inserted_count():
    payload = [
        tea_payload("Darjeeling", "India"),
        tea_payload("Assam", "India"),
        tea_payload("Sencha", "Japan"),
    ]

    response = client.post("/teas/bulk", json=payload)

    assert response.status_code == 201
    assert response.json() == {"inserted": 3}
    assert [tea["id"] for tea in client.get("/teas").json()] == [1, 2, 3]


def test_bulk_count_is_not_total_inventory_count():
    client.post("/teas", json=tea_payload("Darjeeling", "India"))

    response = client.post(
        "/teas/bulk",
        json=[
            tea_payload("Assam", "India"),
            tea_payload("Sencha", "Japan"),
        ],
    )

    assert response.status_code == 201
    assert response.json() == {"inserted": 2}
    assert len(client.get("/teas").json()) == 3


def test_empty_bulk_request_reports_zero_inserted():
    response = client.post("/teas/bulk", json=[])

    assert response.status_code == 200
    assert response.json() == {
        "inserted": 0,
        "message": "No teas were submitted; nothing was inserted.",
    }
    assert client.get("/teas").json() == []


def test_bulk_with_existing_name_aborts_entire_batch():
    client.post("/teas", json=tea_payload("Assam Black", "Assam"))

    response = client.post(
        "/teas/bulk",
        json=[
            tea_payload("Darjeeling", "India"),
            tea_payload("Assam Black", "India"),
        ],
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["message"] == "Bulk insertion aborted. No teas were inserted."
    assert "Assam Black" in detail["reason"]

    teas = client.get("/teas").json()
    assert len(teas) == 1
    assert teas[0]["name"] == "Assam Black"


def test_bulk_with_repeated_name_aborts_entire_batch():
    response = client.post(
        "/teas/bulk",
        json=[
            tea_payload("Darjeeling", "India"),
            tea_payload("Darjeeling", "West Bengal"),
        ],
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["message"] == "Bulk insertion aborted. No teas were inserted."
    assert client.get("/teas").json() == []


def test_invalid_bulk_payload_inserts_nothing():
    response = client.post(
        "/teas/bulk",
        json=[
            tea_payload("Darjeeling", "India"),
            {"name": "Incomplete tea"},
        ],
    )

    assert response.status_code == 422
    assert client.get("/teas").json() == []


def test_update_existing_tea():
    client.post("/teas", json=tea_payload("Darjeeling", "India"))

    response = client.put(
        "/teas/1",
        json=tea_payload("Darjeeling First Flush", "West Bengal, India"),
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "name": "Darjeeling First Flush",
        "origin": "West Bengal, India",
    }


def test_update_missing_tea_returns_404():
    response = client.put(
        "/teas/999",
        json=tea_payload("Darjeeling", "India"),
    )

    assert response.status_code == 404


def test_update_to_an_existing_name_returns_conflict():
    client.post("/teas", json=tea_payload("Darjeeling", "India"))
    client.post("/teas", json=tea_payload("Assam", "India"))

    response = client.put(
        "/teas/2",
        json=tea_payload("Darjeeling", "India"),
    )

    assert response.status_code == 409
    teas = client.get("/teas").json()
    assert [(tea["id"], tea["name"]) for tea in teas] == [
        (1, "Darjeeling"),
        (2, "Assam"),
    ]


def test_update_invalid_payload_returns_422():
    client.post("/teas", json=tea_payload())

    response = client.put("/teas/1", json={"name": "Updated name"})

    assert response.status_code == 422


def test_delete_existing_tea():
    client.post("/teas", json=tea_payload("Darjeeling", "India"))
    client.post("/teas", json=tea_payload("Assam", "India"))

    response = client.delete("/teas/1")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Successfully deleted tea item with ID 1"
    }
    assert [tea["id"] for tea in client.get("/teas").json()] == [2]


def test_delete_missing_tea_returns_404():
    response = client.delete("/teas/999")

    assert response.status_code == 404
    assert client.get("/teas").json() == []