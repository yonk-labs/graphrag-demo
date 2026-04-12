from embeddings import EmbeddingProvider
from models import RetrievedItem
from timing import TimingResult, timed_stage
from db import get_connection


class VectorRetrieval:
    def __init__(self, embedding_provider: EmbeddingProvider):
        self.embedding_provider = embedding_provider

    def retrieve(
        self, question: str, top_k: int, timing: TimingResult
    ) -> list[RetrievedItem]:
        with timed_stage(timing, "embedding"):
            query_embedding = self.embedding_provider.embed(question)

        with timed_stage(timing, "vector_search"):
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT title, content, doc_type,
                               1 - (embedding <=> %s::vector) AS similarity,
                               author_id, project_id
                        FROM documents
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (str(query_embedding), str(query_embedding), top_k),
                    )
                    rows = cur.fetchall()

        return [
            RetrievedItem(
                title=row[0],
                content=row[1],
                doc_type=row[2],
                score=round(row[3], 4),
                source="vector",
                explanation=f"Cosine similarity: {row[3]:.4f}",
            )
            for row in rows
        ]
