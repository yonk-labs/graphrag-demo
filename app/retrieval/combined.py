from typing import Callable

from models import RetrievedItem
from timing import TimingResult, timed_stage
from db import get_connection
from retrieval.vector import VectorRetrieval
from retrieval.graph import GraphRetrieval


def rerank_results(
    items: list[RetrievedItem],
    vector_weight: float = 0.6,
    graph_weight: float = 0.4,
) -> list[RetrievedItem]:
    """
    Re-rank results by combining vector similarity and graph proximity.
    Deduplicates by title, keeping the highest-scoring version.
    """
    # Deduplicate: keep best score per title, but prefer complementary sources
    # (so a doc found by BOTH vector and graph keeps the higher-weighted score)
    best_by_title: dict[str, RetrievedItem] = {}
    for item in items:
        existing = best_by_title.get(item.title)
        if existing is None or item.score > existing.score:
            best_by_title[item.title] = item

    # Re-score based on source
    reranked = []
    for item in best_by_title.values():
        if item.source == "vector":
            combined_score = item.score * vector_weight
        elif item.source == "graph":
            combined_score = item.score * graph_weight
        elif item.source == "graph_expanded":
            combined_score = item.score * graph_weight * 0.7
        else:
            combined_score = item.score

        reranked.append(RetrievedItem(
            title=item.title,
            content=item.content,
            doc_type=item.doc_type,
            score=round(combined_score, 4),
            source="graph+vector",
            explanation=f"Combined: {item.explanation}",
        ))

    reranked.sort(key=lambda x: x.score, reverse=True)
    return reranked


def _default_graph_expand(conn, author_id: str, project_id: str | None) -> list[RetrievedItem]:
    """Expand from a document's author/project into the graph, find related docs."""
    results = []
    entity_ids = [author_id]
    if project_id:
        entity_ids.append(project_id)

    with conn.cursor() as cur:
        # Find people connected to the author (same team, same project)
        cur.execute(
            "SELECT * FROM cypher('org_graph', $$ "
            f"MATCH (p:Person {{id: '{author_id}'}})-[:MEMBER_OF]->(t:Team)<-[:MEMBER_OF]-(colleague:Person) "
            "WHERE colleague <> p "
            "RETURN colleague.id "
            "$$) AS (id agtype);"
        )
        colleague_ids = [str(row[0]).strip('"') for row in cur.fetchall()]

        # Find projects connected to the author's projects
        connected_project_ids = []
        if project_id:
            cur.execute(
                "SELECT * FROM cypher('org_graph', $$ "
                f"MATCH (p:Project {{id: '{project_id}'}})-[:DEPENDS_ON]->(s:Service)<-[:DEPENDS_ON]-(p2:Project) "
                "WHERE p2 <> p "
                "RETURN p2.id "
                "$$) AS (id agtype);"
            )
            connected_project_ids = [str(row[0]).strip('"') for row in cur.fetchall()]

        # Fetch documents from expanded entities
        all_ids = list(set(colleague_ids + connected_project_ids + entity_ids))
        if all_ids:
            placeholders = ",".join(["%s"] * len(all_ids))
            cur.execute(
                f"SELECT title, content, doc_type, author_id, project_id "
                f"FROM documents "
                f"WHERE author_id IN ({placeholders}) OR project_id IN ({placeholders}) "
                f"LIMIT 20",
                all_ids + all_ids,
            )
            for row in cur.fetchall():
                hop_count = 1 if row[3] in entity_ids or row[4] in entity_ids else 2
                results.append(RetrievedItem(
                    title=row[0],
                    content=row[1],
                    doc_type=row[2],
                    score=1.0 / (1 + hop_count),
                    source="graph_expanded",
                    explanation=f"Graph expansion: {hop_count} hop(s) from seed",
                ))

    return results


class CombinedRetrieval:
    def __init__(
        self,
        vector_retrieval: VectorRetrieval,
        graph_retrieval: GraphRetrieval | None = None,
        graph_expand_fn: Callable | None = None,
    ):
        self.vector_retrieval = vector_retrieval
        self.graph_retrieval = graph_retrieval
        self.graph_expand_fn = graph_expand_fn or _default_graph_expand

    def retrieve(
        self, question: str, top_k: int, timing: TimingResult
    ) -> list[RetrievedItem]:
        # Stage 1+2: Vector search (semantic seeds)
        vector_results = self.vector_retrieval.retrieve(question, top_k=top_k, timing=timing)

        # Stage 3: Graph entity search (structural seeds from question entities)
        graph_results: list[RetrievedItem] = []
        with timed_stage(timing, "graph_entity_search"):
            if self.graph_retrieval is not None:
                try:
                    sub_timing = TimingResult()
                    graph_results = self.graph_retrieval.retrieve(
                        question, top_k=top_k, timing=sub_timing
                    )
                except Exception:
                    graph_results = []

        # Stage 4: Graph expansion from vector seed results
        graph_expanded: list[RetrievedItem] = []
        with timed_stage(timing, "graph_expansion"):
            if vector_results:
                try:
                    with get_connection() as conn:
                        seen_titles = {r.title for r in vector_results} | {r.title for r in graph_results}
                        for vr in vector_results[:5]:
                            with conn.cursor() as cur:
                                cur.execute(
                                    "SELECT author_id, project_id FROM documents WHERE title = %s LIMIT 1",
                                    (vr.title,),
                                )
                                row = cur.fetchone()
                                if row:
                                    expanded = self.graph_expand_fn(conn, row[0], row[1])
                                    for item in expanded:
                                        if item.title not in seen_titles:
                                            graph_expanded.append(item)
                                            seen_titles.add(item.title)
                except Exception:
                    pass

        # Stage 5: Re-rank combined results
        with timed_stage(timing, "reranking"):
            all_results = vector_results + graph_results + graph_expanded
            reranked = rerank_results(all_results)

        return reranked[:top_k]
