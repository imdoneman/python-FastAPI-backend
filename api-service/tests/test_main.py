import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from main import app

# Standard FastAPI test client
client = TestClient(app)

def test_pulse_check():
    """Ensure the API boots and routes correctly."""
    response = client.get("/pulse")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

@patch("main.publish_to_queue")
def test_create_tea_queues_message(mock_publish):
    """
    Proves that a POST request doesn't touch a DB, 
    but instead successfully hands the payload to the RabbitMQ producer.
    """
    payload = {"name": "Test Matcha", "origin": "Japan"}
    response = client.post("/teas", json=payload)
    
    assert response.status_code == 202
    assert response.json()["status"] == "Accepted"
    
    # Assert the mock publisher was called with the exact right parameters
    mock_publish.assert_called_once_with(action="create", payload=payload)

@patch("main.httpx2.AsyncClient.get")
@pytest.mark.asyncio
async def test_get_teas_fetches_from_worker(mock_get):
    """
    Proves that a GET request makes an internal network call 
    to the worker service instead of querying a database.
    """
    # Build a fake HTTPX response
    mock_response = MagicMock()
    mock_response.json.return_value = [{"id": 1, "name": "Fake Tea", "origin": "Fake Origin"}]
    mock_response.raise_for_status.return_value = None
    
    # Configure the mocked async context manager
    mock_get.return_value = mock_response

    # Trigger the route
    response = client.get("/teas")
    
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["name"] == "Fake Tea"

@patch("main.publish_to_queue")
def test_add_multiple_teas_queues_message(mock_publish):
    """Proves the bulk endpoint correctly maps a list to the publisher."""
    payload = [
        {"name": "Bulk Tea 1", "origin": "India"},
        {"name": "Bulk Tea 2", "origin": "China"}
    ]
    response = client.post("/teas/bulk", json=payload)
    
    assert response.status_code == 202
    assert response.json()["status"] == "Accepted"
    
    # Assert it passed the exact list to the queue
    mock_publish.assert_called_once_with(action="bulk_create", payload=payload)


@patch("main.publish_to_queue")
def test_update_tea_queues_message(mock_publish):
    """Proves the PUT endpoint bundles the ID and the new data correctly."""
    tea_id = 1
    updated_payload = {"name": "Updated Earl Grey", "origin": "UK"}
    
    response = client.put(f"/teas/{tea_id}", json=updated_payload)
    
    assert response.status_code == 202
    assert response.json()["status"] == "Accepted"
    
    # Assert the API bundled the ID into the payload dictionary correctly
    expected_queue_payload = {
        "id": tea_id,
        "update_data": updated_payload
    }
    mock_publish.assert_called_once_with(action="update", payload=expected_queue_payload)


@patch("main.publish_to_queue")
def test_delete_tea_queues_message(mock_publish):
    """Proves the DELETE endpoint sends just the ID to the queue."""
    tea_id = 99
    
    response = client.delete(f"/teas/{tea_id}")
    
    assert response.status_code == 202
    assert response.json()["status"] == "Accepted"
    
    mock_publish.assert_called_once_with(action="delete", payload={"id": tea_id})