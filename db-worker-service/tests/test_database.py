import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import models
import worker
from database import Base, get_db


test_engine = create_engine(
    "sqlite:///:memory:",
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


worker.app.dependency_overrides[get_db] = override_get_db
client = TestClient(worker.app)


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


def test_worker_pulse():
    response = client.get("/pulse")

    assert response.status_code == 200
    assert response.json()["status"] == "worker_online"


def test_internal_get_teas_empty():
    response = client.get("/internal/teas")

    assert response.status_code == 200
    assert response.json() == []


def test_internal_get_teas_with_data():
    db = TestingSessionLocal()
    try:
        db.add(
            models.TeaItem(
                name="Earl Grey Test",
                origin="UK",
            )
        )
        db.commit()
    finally:
        db.close()

    response = client.get("/internal/teas")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "name": "Earl Grey Test",
            "origin": "UK",
        }
    ]


def test_process_create_acknowledges_successful_message():
    channel = MagicMock()
    method = MagicMock(delivery_tag=123)

    with patch.object(
        worker,
        "SessionLocal",
        TestingSessionLocal,
    ):
        worker.process_task(
            channel,
            method,
            None,
            json.dumps(
                {
                    "action": "create",
                    "data": {
                        "name": "Assam",
                        "origin": "India",
                    },
                }
            ).encode(),
        )

    channel.basic_ack.assert_called_once_with(delivery_tag=123)
    channel.basic_reject.assert_not_called()
    channel.basic_nack.assert_not_called()

    db = TestingSessionLocal()
    try:
        assert (
            db.query(models.TeaItem)
            .filter_by(name="Assam")
            .first()
            is not None
        )
    finally:
        db.close()


def test_process_duplicate_create_is_idempotent():
    db = TestingSessionLocal()
    try:
        db.add(models.TeaItem(name="Assam", origin="India"))
        db.commit()
    finally:
        db.close()

    channel = MagicMock()
    method = MagicMock(delivery_tag=124)

    with patch.object(
        worker,
        "SessionLocal",
        TestingSessionLocal,
    ):
        worker.process_task(
            channel,
            method,
            None,
            json.dumps(
                {
                    "action": "create",
                    "data": {
                        "name": "Assam",
                        "origin": "India",
                    },
                }
            ).encode(),
        )

    channel.basic_ack.assert_called_once_with(delivery_tag=124)

    db = TestingSessionLocal()
    try:
        assert db.query(models.TeaItem).filter_by(name="Assam").count() == 1
    finally:
        db.close()


def test_process_rejects_unknown_action():
    channel = MagicMock()
    method = MagicMock(delivery_tag=125)

    worker.process_task(
        channel,
        method,
        None,
        json.dumps(
            {"action": "unknown", "data": {}}
        ).encode(),
    )

    channel.basic_reject.assert_called_once_with(
        delivery_tag=125,
        requeue=False,
    )
    channel.basic_ack.assert_not_called()


def test_process_rejects_invalid_json():
    channel = MagicMock()
    method = MagicMock(delivery_tag=126)

    worker.process_task(
        channel,
        method,
        None,
        b"{not valid JSON",
    )

    channel.basic_reject.assert_called_once_with(
        delivery_tag=126,
        requeue=False,
    )