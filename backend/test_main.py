"""Integration tests for the Expense Tracker API.
Run: pytest test_main.py -v
"""

import os
import uuid
import tempfile
import pytest
from fastapi.testclient import TestClient

# Use a temporary file DB for tests so SQLite persists across separate request
# connections during the test run.
db_file = tempfile.NamedTemporaryFile(prefix="test_expenses_", suffix=".db", delete=False)
db_file.close()
os.environ["DB_PATH"] = db_file.name

from main import app, init_db

init_db()
client = TestClient(app)


def teardown_module(module):
    try:
        os.remove(db_file.name)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def reset_db():
    """Recreate tables before each test."""
    init_db()
    yield


def test_create_expense():
    resp = client.post("/expenses", json={
        "amount": "250.50",
        "category": "Food",
        "description": "Lunch",
        "date": "2025-04-28",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["amount"] == "250.50"
    assert data["category"] == "Food"
    assert "id" in data


def test_idempotency_key_prevents_duplicate():
    key = str(uuid.uuid4())
    payload = {
        "amount": "100.00",
        "category": "Transport",
        "description": "Cab",
        "date": "2025-04-28",
        "idempotency_key": key,
    }
    r1 = client.post("/expenses", json=payload)
    r2 = client.post("/expenses", json=payload)
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.json()["id"] == r2.json()["id"]  # same record returned


def test_negative_amount_rejected():
    resp = client.post("/expenses", json={
        "amount": "-50",
        "category": "Food",
        "description": "Bad",
        "date": "2025-04-28",
    })
    assert resp.status_code == 422


def test_zero_amount_rejected():
    resp = client.post("/expenses", json={
        "amount": "0",
        "category": "Food",
        "description": "Bad",
        "date": "2025-04-28",
    })
    assert resp.status_code == 422


def test_invalid_date_rejected():
    resp = client.post("/expenses", json={
        "amount": "100",
        "category": "Food",
        "description": "Test",
        "date": "28-04-2025",  # wrong format
    })
    assert resp.status_code == 422


def test_filter_by_category():
    client.post("/expenses", json={"amount": "100", "category": "Food", "description": "A", "date": "2025-04-01"})
    client.post("/expenses", json={"amount": "200", "category": "Travel", "description": "B", "date": "2025-04-02"})

    resp = client.get("/expenses?category=Food")
    assert resp.status_code == 200
    data = resp.json()
    assert all(e["category"] == "Food" for e in data)


def test_sort_date_desc():
    client.post("/expenses", json={"amount": "100", "category": "Misc", "description": "Old", "date": "2025-01-01"})
    client.post("/expenses", json={"amount": "100", "category": "Misc", "description": "New", "date": "2025-04-28"})

    resp = client.get("/expenses?sort=date_desc")
    assert resp.status_code == 200
    dates = [e["date"] for e in resp.json()]
    assert dates == sorted(dates, reverse=True)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
