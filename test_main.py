from fastapi.testclient import TestClient
from main import app  # Assuming your file is named app.py

client = TestClient(app)


def test_read_root():
    """Verify the home route is accessible."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "welcome to the tea house"}


def test_pulse():
    """Verify the health check/pulse endpoint works for DevOps monitoring."""
    response = client.get("/pulse")
    assert response.status_code == 200
    assert response.json()["status"] == "online"
    assert "uptime" in response.json()


def test_add_and_get_tea():
    """Verify we can add a tea and then retrieve the list."""
    new_tea = {"id": 1, "name": "Darjeeling First Flush",
               "origin": "West Bengal, India"}

    # Test POST
    post_response = client.post("/teas", json=new_tea)
    assert post_response.status_code == 200

    # Test GET
    get_response = client.get("/teas")
    assert len(get_response.json()) > 0
    assert get_response.json()[0]["name"] == "Darjeeling First Flush"


def test_delete_tea():
    """Verify the delete functionality."""
    # Ensure there is a tea to delete
    client.post(
        "/teas", json={"id": 2, "name": "Assam Black", "origin": "Assam, India"})

    response = client.delete("/teas/2")
    assert response.status_code == 200

    # Verify it is gone
    get_response = client.get("/teas")
    assert all(tea["id"] != 2 for tea in get_response.json())
