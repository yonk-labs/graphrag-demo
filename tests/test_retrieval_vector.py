import pytest
from unittest.mock import MagicMock, patch

from retrieval.vector import VectorRetrieval
from timing import TimingResult


@pytest.fixture
def mock_embedding_provider():
    provider = MagicMock()
    provider.embed.return_value = [0.1] * 384
    return provider


@pytest.fixture
def mock_db_results():
    return [
        ("Test Doc 1", "Content about billing migration", "decision_record", 0.92, "p-alice", "proj-billing"),
        ("Test Doc 2", "Content about payment processing", "architecture_doc", 0.85, "p-bob", "proj-billing"),
        ("Test Doc 3", "Meeting notes from sprint", "meeting_note", 0.78, "p-carol", "proj-auth"),
    ]


def test_vector_retrieval_returns_results(mock_embedding_provider, mock_db_results):
    retrieval = VectorRetrieval(mock_embedding_provider)
    timing = TimingResult()

    with patch("retrieval.vector.get_connection") as mock_conn:
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = mock_db_results
        mock_conn.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.return_value.__enter__.return_value.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)

        results = retrieval.retrieve("billing migration status", top_k=5, timing=timing)

    assert len(results) == 3
    assert results[0].source == "vector"
    assert results[0].score == 0.92
    assert "embedding" in timing.stages
    assert "vector_search" in timing.stages


def test_vector_retrieval_calls_embed(mock_embedding_provider):
    retrieval = VectorRetrieval(mock_embedding_provider)
    timing = TimingResult()

    with patch("retrieval.vector.get_connection") as mock_conn:
        mock_cur = MagicMock()
        mock_cur.fetchall.return_value = []
        mock_conn.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_conn.return_value.__enter__.return_value.cursor.return_value.__enter__ = MagicMock(return_value=mock_cur)
        mock_conn.return_value.__enter__.return_value.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.__exit__ = MagicMock(return_value=False)

        retrieval.retrieve("test query", top_k=5, timing=timing)

    mock_embedding_provider.embed.assert_called_once_with("test query")
