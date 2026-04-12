import pytest
from unittest.mock import MagicMock, patch

from retrieval.graph import GraphRetrieval, extract_entities
from timing import TimingResult


def test_extract_entities_finds_known_names():
    known_entities = {
        "people": {"alice chen": "p-alice", "bob martinez": "p-bob"},
        "projects": {"billing migration": "proj-billing"},
        "services": {"payment service": "svc-payment", "auth service": "svc-auth"},
        "teams": {"engineering": "team-eng", "data": "team-data"},
        "technologies": {"postgresql": "tech-postgres"},
    }
    question = "Who on the data team knows about the payment service?"
    entities = extract_entities(question, known_entities)

    assert ("Team", "team-data") in entities
    assert ("Service", "svc-payment") in entities


def test_extract_entities_handles_no_match():
    known_entities = {
        "people": {"alice chen": "p-alice"},
        "projects": {},
        "services": {},
        "teams": {},
        "technologies": {},
    }
    entities = extract_entities("something completely unrelated", known_entities)
    assert len(entities) == 0


def test_graph_retrieval_records_timing():
    retrieval = GraphRetrieval()
    timing = TimingResult()

    with patch("retrieval.graph.get_connection") as mock_conn:
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = []
        mock_conn.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.return_value.__enter__.return_value.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)

        with patch("retrieval.graph._load_known_entities", return_value={
            "people": {}, "projects": {}, "services": {}, "teams": {}, "technologies": {}
        }):
            results = retrieval.retrieve("test query", top_k=5, timing=timing)

    assert "entity_extraction" in timing.stages
    assert "graph_traversal" in timing.stages
