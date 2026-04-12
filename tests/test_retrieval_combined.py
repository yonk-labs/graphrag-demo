import pytest
from unittest.mock import MagicMock

from retrieval.combined import CombinedRetrieval, rerank_results
from models import RetrievedItem
from timing import TimingResult


def test_rerank_results_combines_scores():
    items = [
        RetrievedItem(
            title="Doc A", content="content a", doc_type="meeting_note",
            score=0.9, source="vector", explanation="cosine: 0.9"
        ),
        RetrievedItem(
            title="Doc B", content="content b", doc_type="architecture_doc",
            score=0.5, source="graph_expanded", explanation="2 hops away"
        ),
        RetrievedItem(
            title="Doc C", content="content c", doc_type="decision_record",
            score=0.7, source="vector", explanation="cosine: 0.7"
        ),
    ]

    reranked = rerank_results(items, vector_weight=0.6, graph_weight=0.4)
    assert len(reranked) == 3
    assert all(r.source == "graph+vector" for r in reranked)


def test_rerank_deduplicates_by_title():
    items = [
        RetrievedItem(
            title="Same Doc", content="content", doc_type="meeting_note",
            score=0.9, source="vector", explanation="cosine: 0.9"
        ),
        RetrievedItem(
            title="Same Doc", content="content", doc_type="meeting_note",
            score=0.5, source="graph_expanded", explanation="1 hop"
        ),
    ]

    reranked = rerank_results(items, vector_weight=0.6, graph_weight=0.4)
    assert len(reranked) == 1


def test_combined_retrieval_records_all_timing_stages():
    mock_vector = MagicMock()
    mock_vector.retrieve.return_value = [
        RetrievedItem(
            title="Doc A", content="about billing", doc_type="meeting_note",
            score=0.9, source="vector", explanation="cosine: 0.9"
        ),
    ]

    mock_graph_expand = MagicMock(return_value=[])

    retrieval = CombinedRetrieval(
        vector_retrieval=mock_vector,
        graph_expand_fn=mock_graph_expand,
    )
    timing = TimingResult()
    results = retrieval.retrieve("billing question", top_k=5, timing=timing)

    assert "graph_expansion" in timing.stages
    assert "reranking" in timing.stages
