"""
Hybrid retrieval: combines pgvector cosine similarity with Postgres full-text search (BM25-like).
Uses reciprocal rank fusion (RRF) to merge the two ranked lists.
"""

from embeddings import EmbeddingProvider
from models import RetrievedItem
from timing import TimingResult, timed_stage
from db import get_connection

RRF_K = 60  # RRF constant


class HybridRetrieval:
    def __init__(self, embedding_provider: EmbeddingProvider):
        self.embedding_provider = embedding_provider

    def retrieve(
        self, question: str, top_k: int, timing: TimingResult
    ) -> list[RetrievedItem]:
        # Stage 1: Embed the question
        with timed_stage(timing, "embedding"):
            query_embedding = self.embedding_provider.embed(question)

        # Stage 2: Vector search
        with timed_stage(timing, "vector_search"):
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, title, content, doc_type,
                               1 - (embedding <=> %s::vector) AS similarity
                        FROM documents
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (str(query_embedding), str(query_embedding), top_k * 3),
                    )
                    vector_rows = cur.fetchall()

        # Stage 3: Full-text search
        with timed_stage(timing, "fulltext_search"):
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, title, content, doc_type,
                               ts_rank_cd(
                                   to_tsvector('english', title || ' ' || content),
                                   plainto_tsquery('english', %s)
                               ) AS rank
                        FROM documents
                        WHERE to_tsvector('english', title || ' ' || content) @@ plainto_tsquery('english', %s)
                        ORDER BY rank DESC
                        LIMIT %s
                        """,
                        (question, question, top_k * 3),
                    )
                    fts_rows = cur.fetchall()

        # Stage 4: Reciprocal Rank Fusion
        with timed_stage(timing, "rrf_fusion"):
            scores: dict = {}
            details: dict = {}

            for rank, row in enumerate(vector_rows, start=1):
                doc_id = str(row[0])
                scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (RRF_K + rank)
                details[doc_id] = {
                    "title": row[1],
                    "content": row[2],
                    "doc_type": row[3],
                    "vector_sim": float(row[4]),
                    "vector_rank": rank,
                }

            for rank, row in enumerate(fts_rows, start=1):
                doc_id = str(row[0])
                scores[doc_id] = scores.get(doc_id, 0) + 1.0 / (RRF_K + rank)
                if doc_id not in details:
                    details[doc_id] = {
                        "title": row[1],
                        "content": row[2],
                        "doc_type": row[3],
                        "vector_sim": None,
                        "vector_rank": None,
                    }
                details[doc_id]["fts_rank"] = rank
                details[doc_id]["fts_rank_score"] = float(row[4])

            sorted_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for doc_id, score in sorted_ids:
            d = details[doc_id]
            signals = []
            if d.get("vector_rank"):
                signals.append(f"vector #{d['vector_rank']}")
            if d.get("fts_rank"):
                signals.append(f"fulltext #{d['fts_rank']}")
            results.append(RetrievedItem(
                title=d["title"],
                content=d["content"],
                doc_type=d["doc_type"],
                score=round(score, 4),
                source="hybrid",
                explanation=f"RRF fusion: {' + '.join(signals)}",
            ))

        return results
