
import re

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture(autouse=True)
def reset_inventory():
    """Give every test a clean in-memory inventory."""
    main.teas.clear()
    main.next_tea_id = 1
    yield
    main.teas.clear()
    main.next_tea_id = 1


client = TestClient(main.app)


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
    assert re.fullmatch(r"\d+s", data["uptime"])
    assert data["version"] == "1.1.0"


def test_get_teas_initially_returns_empty_list():
    response = client.get("/teas")

    assert response.status_code == 200
    assert response.json() == []


def test_create_single_tea_returns_insert_count_not_id():
    response = client.post("/teas", json=tea_payload())

    assert response.status_code == 201
    assert response.json() == {"inserted": 1}

    teas_response = client.get("/teas")
    assert teas_response.status_code == 200
    assert teas_response.json() == [
        {
            "id": 1,
            "name": "Darjeeling First Flush",
            "origin": "West Bengal, India",
        }
    ]


def test_generated_ids_are_unique_and_increasing():
    first = client.post("/teas", json=tea_payload("Darjeeling", "India"))
    second = client.post("/teas", json=tea_payload("Assam", "India"))

    assert first.json() == {"inserted": 1}
    assert second.json() == {"inserted": 1}

    teas = client.get("/teas").json()
    assert [tea["id"] for tea in teas] == [1, 2]


def test_bulk_create_returns_batch_count_not_ids():
    payload = [
        tea_payload("Darjeeling", "India"),
        tea_payload("Assam", "India"),
        tea_payload("Sencha", "Japan"),
    ]

    response = client.post("/teas/bulk", json=payload)

    assert response.status_code == 201
    assert response.json() == {"inserted": 3}

    teas = client.get("/teas").json()
    assert len(teas) == 3
    assert [tea["id"] for tea in teas] == [1, 2, 3]


def test_bulk_create_count_is_not_total_inventory_count():
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


def test_bulk_create_empty_list_inserts_zero():
    response = client.post("/teas/bulk", json=[])

    assert response.status_code == 200
    assert response.json() == {"inserted": 0}
    assert client.get("/teas").json() == []


def test_invalid_single_tea_is_rejected_without_insertion():
    response = client.post(
        "/teas",
        json={"name": "Darjeeling"},  # origin is missing
    )

    assert response.status_code == 422
    assert client.get("/teas").json() == []


def test_invalid_bulk_request_is_rejected_without_partial_insertion():
    response = client.post(
        "/teas/bulk",
        json=[
            tea_payload("Darjeeling", "India"),
            {"name": "Incomplete tea"},  # origin is missing
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
    assert response.json() == [
        {
            "id": 1,
            "name": "Darjeeling First Flush",
            "origin": "West Bengal, India",
        }
    ]


def test_update_missing_tea_returns_404():
    response = client.put(
        "/teas/999",
        json=tea_payload("Darjeeling", "India"),
    )

    assert response.status_code == 404
    assert client.get("/teas").json() == []


def test_update_rejects_invalid_body():
    client.post("/teas", json=tea_payload())

    response = client.put(
        "/teas/1",
        json={"name": "Updated name"},  # origin is missing
    )

    assert response.status_code == 422


def test_delete_existing_tea():
    client.post("/teas", json=tea_payload("Darjeeling", "India"))
    client.post("/teas", json=tea_payload("Assam", "India"))

    response = client.delete("/teas/1")

    assert response.status_code == 200
    assert [tea["id"] for tea in response.json()] == [2]
    assert [tea["id"] for tea in client.get("/teas").json()] == [2]


def test_delete_missing_tea_returns_404():
    response = client.delete("/teas/999")

    assert response.status_code == 404
    assert client.get("/teas").json() == []
