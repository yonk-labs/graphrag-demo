import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_query_endpoint_returns_four_strategies():
    mock_results = []
    mock_timing_dict = {"embedding": 5.0, "vector_search": 10.0, "total": 15.0}

    with patch("main._run_strategy") as mock_run:
        mock_run.return_value = {
            "strategy": "vector",
            "results": [],
            "answer": "Test answer",
            "timing": mock_timing_dict,
        }

        response = client.post("/api/query", json={"question": "test question"})

    assert response.status_code == 200
    data = response.json()
    assert data["question"] == "test question"
    assert len(data["strategies"]) == 4


def test_query_endpoint_rejects_empty_question():
    response = client.post("/api/query", json={"question": ""})
    assert response.status_code in (400, 422)


def test_example_queries_endpoint():
    response = client.get("/api/examples")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all("question" in q for q in data)
