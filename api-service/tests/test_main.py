
from unittest.mock import AsyncMock, MagicMock, patch

import httpx2
from fastapi.testclient import TestClient

from main import app
from producer import RabbitMQPublishError


client = TestClient(app)


def test_pulse_check():
    response = client.get("/pulse")

    assert response.status_code == 200
    assert response.json()["status"] == "online"
    assert response.json()["version"] == "3.1.0"


@patch("main.publish_to_queue")
def test_create_tea_queues_message(mock_publish):
    payload = {"name": "Test Matcha", "origin": "Japan"}

    response = client.post("/teas", json=payload)

    assert response.status_code == 202
    assert response.json()["status"] == "Accepted"
    mock_publish.assert_called_once_with(
        action="create",
        payload=payload,
    )


@patch(
    "main.publish_to_queue",
    side_effect=RabbitMQPublishError("broker unavailable"),
)
def test_create_tea_returns_503_when_broker_fails(mock_publish):
    response = client.post(
        "/teas",
        json={"name": "Test Matcha", "origin": "Japan"},
    )

    assert response.status_code == 503
    assert "broker" in response.json()["detail"].lower()
    mock_publish.assert_called_once()


@patch("main.publish_to_queue")
def test_bulk_create_queues_message(mock_publish):
    payload = [
        {"name": "Bulk Tea 1", "origin": "India"},
        {"name": "Bulk Tea 2", "origin": "China"},
    ]

    response = client.post("/teas/bulk", json=payload)

    assert response.status_code == 202
    mock_publish.assert_called_once_with(
        action="bulk_create",
        payload=payload,
    )


def test_bulk_create_rejects_empty_list():
    response = client.post("/teas/bulk", json=[])

    assert response.status_code == 422


@patch("main.publish_to_queue")
def test_update_tea_queues_message(mock_publish):
    tea_id = 1
    payload = {"name": "Updated Earl Grey", "origin": "UK"}

    response = client.put(f"/teas/{tea_id}", json=payload)

    assert response.status_code == 202
    mock_publish.assert_called_once_with(
        action="update",
        payload={
            "id": tea_id,
            "update_data": payload,
        },
    )


def test_update_rejects_nonpositive_id():
    response = client.put(
        "/teas/0",
        json={"name": "Earl Grey", "origin": "UK"},
    )

    assert response.status_code == 422


@patch("main.publish_to_queue")
def test_delete_tea_queues_message(mock_publish):
    response = client.delete("/teas/99")

    assert response.status_code == 202
    mock_publish.assert_called_once_with(
        action="delete",
        payload={"id": 99},
    )


@patch("main.httpx2.AsyncClient.get", new_callable=AsyncMock)
def test_get_teas_fetches_from_worker(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = [
        {"id": 1, "name": "Fake Tea", "origin": "Fake Origin"}
    ]
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    response = client.get("/teas")

    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "name": "Fake Tea", "origin": "Fake Origin"}
    ]
    mock_get.assert_awaited_once_with(
        "http://db-worker-service:8080/internal/teas"
    )


@patch(
    "main.httpx2.AsyncClient.get",
    new_callable=AsyncMock,
    side_effect=httpx2.ConnectError("worker unavailable"),
)
def test_get_teas_returns_503_when_worker_is_unreachable(mock_get):
    response = client.get("/teas")

    assert response.status_code == 503
    mock_get.assert_awaited_once()


@patch(
    "main.httpx2.AsyncClient.get",
    new_callable=AsyncMock,
    side_effect=httpx2.ReadTimeout("worker timed out"),
)
def test_get_teas_returns_504_when_worker_times_out(mock_get):
    response = client.get("/teas")

    assert response.status_code == 504
    mock_get.assert_awaited_once()


@patch("main.httpx2.AsyncClient.get", new_callable=AsyncMock)
def test_get_teas_returns_502_when_worker_returns_http_error(mock_get):
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = httpx2.HTTPStatusError(
        "upstream failure",
        request=MagicMock(),
        response=MagicMock(),
    )
    mock_get.return_value = mock_response

    response = client.get("/teas")

    assert response.status_code == 502
    mock_get.assert_awaited_once()


def test_metrics_exposed():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text or "http_request_duration_seconds" in response.text
