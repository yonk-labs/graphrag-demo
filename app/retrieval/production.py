"""
Production-grade 3-stage retrieval.

Stage 1: Hybrid (vector + BM25) always runs.
Stage 2: Cheap graph boost on top-K entities.
Stage 3: Conditional graph expand - only when triggered by query shape, weak
         confidence, or explicit request.
"""

import re

from models import RetrievedItem
from timing import TimingResult, timed_stage
from db import get_connection
from retrieval.hybrid import HybridRetrieval
from retrieval.graph import GraphRetrieval, _load_known_entities, extract_entities


# Threshold below which vector confidence is considered weak
WEAK_CONFIDENCE_THRESHOLD = 0.5

# Patterns that suggest graph-shaped questions
GRAPH_SHAPED_PATTERNS = [
    r"\bwho (owns|wrote|voted|dissented|cited|reports|manages|approved|authored)\b",
    r"\bwhat (depends on|cites|connects|owns|manages)\b",
    r"\bwhich (justices|cases|services|projects|people) (voted|dissented|cited|own)\b",
    r"\b(cases|people|services) (where|that) (both|all|together)\b",
    r"\band\s+justice\s+\w+",
    r"\bvoted (with|against|together)\b",
    r"\bcited (by|in)\b",
    r"\bdepends on\b",
    r"\bwho should i talk to\b",
    r"\bblast radius\b",
]


def _matches_graph_pattern(question: str) -> bool:
    q_lower = question.lower()
    for pattern in GRAPH_SHAPED_PATTERNS:
        if re.search(pattern, q_lower):
            return True
    return False


def _stage2_graph_boost(
    cur,
    results: list[RetrievedItem],
    known_entities: dict,
    boost_factor: float = 1.2,
) -> list[RetrievedItem]:
    """
    For each result, find entity mentions, look up 1-hop neighbors, boost scores
    if other results mention those neighbors.
    """
    if not results:
        return results

    result_entities: list[set[tuple[str, str]]] = []
    for item in results:
        text = f"{item.title} {item.content}".lower()
        matched = set()
        for category, name_map in known_entities.items():
            for name, entity_id in name_map.items():
                if name and name in text:
                    matched.add((category, entity_id))
        result_entities.append(matched)

    unique_entities: set[tuple[str, str]] = set()
    for entities in result_entities:
        unique_entities.update(entities)

    neighbor_cache: dict[tuple[str, str], set[str]] = {}
    label_map = {
        "people": "Person",
        "projects": "Project",
        "services": "Service",
        "teams": "Team",
        "technologies": "Technology",
        "cases": "Case",
        "justices": "Justice",
        "issues": "Issue",
    }

    for category, entity_id in unique_entities:
        label = label_map.get(category, "")
        if not label:
            continue
        try:
            cur.execute(
                f"SELECT * FROM cypher('org_graph', $$ "
                f"MATCH (n:{label} {{id: '{entity_id}'}})-[]-(m) "
                f"RETURN m.name "
                f"$$) AS (name agtype);"
            )
            neighbors = set()
            for row in cur.fetchall():
                name = str(row[0]).strip('"').lower()
                if name and name != "null":
                    neighbors.add(name)
            neighbor_cache[(category, entity_id)] = neighbors
        except Exception:
            neighbor_cache[(category, entity_id)] = set()

    boosted = []
    for i, item in enumerate(results):
        text = f"{item.title} {item.content}".lower()
        boost_applied = False
        for j, other_entities in enumerate(result_entities):
            if i == j:
                continue
            for ent_key in other_entities:
                neighbors = neighbor_cache.get(ent_key, set())
                for neighbor_name in neighbors:
                    if neighbor_name in text:
                        boost_applied = True
                        break
                if boost_applied:
                    break
            if boost_applied:
                break

        new_score = item.score * boost_factor if boost_applied else item.score
        explanation = item.explanation
        if boost_applied:
            explanation = f"{item.explanation} [graph boost x{boost_factor}]"

        boosted.append(RetrievedItem(
            title=item.title,
            content=item.content,
            doc_type=item.doc_type,
            score=round(new_score, 4),
            source=item.source,
            explanation=explanation,
        ))

    boosted.sort(key=lambda x: x.score, reverse=True)
    return boosted


def _should_run_stage3(
    question: str,
    stage1_results: list[RetrievedItem],
    expand_explicit: bool,
    known_entities: dict,
    max_vector_sim: float,
) -> tuple[bool, str]:
    """Decide whether Stage 3 should run. Returns (should_run, reason)."""
    if expand_explicit:
        return True, "explicit expand requested"

    if _matches_graph_pattern(question):
        return True, "query matches graph-shaped pattern"

    matches = extract_entities(question, known_entities)
    if len(matches) >= 2:
        return True, f"{len(matches)} entities detected in query"

    # Weak confidence: check the RAW top vector cosine similarity, not the
    # RRF-fused score (which is in the 0.016 range and would always trigger).
    if max_vector_sim < WEAK_CONFIDENCE_THRESHOLD:
        return True, f"weak vector confidence (top cosine {max_vector_sim:.3f})"

    return False, "Stage 1+2 sufficient"


class ProductionRetrieval:
    def __init__(
        self,
        hybrid_retrieval: HybridRetrieval,
        graph_retrieval: GraphRetrieval,
    ):
        self.hybrid_retrieval = hybrid_retrieval
        self.graph_retrieval = graph_retrieval

    def retrieve(
        self,
        question: str,
        top_k: int,
        timing: TimingResult,
        expand_graph: bool = False,
    ) -> tuple[list[RetrievedItem], dict]:
        """
        Run the 3-stage retrieval flow.
        Returns (results, metadata) where metadata includes stage trigger info.
        """
        metadata = {
            "stages_run": ["stage1_hybrid"],
            "stage3_triggered": False,
            "trigger_reason": None,
        }

        # Stage 1: Hybrid (always runs)
        stage1_results = self.hybrid_retrieval.retrieve(question, top_k=top_k * 2, timing=timing)
        for item in stage1_results:
            item.source = "stage1_hybrid"

        # Load known entities once
        with get_connection() as conn:
            with conn.cursor() as cur:
                known_entities = _load_known_entities(cur)

                with timed_stage(timing, "stage2_graph_boost"):
                    boosted_results = _stage2_graph_boost(cur, stage1_results, known_entities)
                metadata["stages_run"].append("stage2_graph_boost")

        # Stage 3: Conditional Graph Expand
        max_vector_sim = self.hybrid_retrieval.last_max_vector_sim
        should_run, reason = _should_run_stage3(
            question, boosted_results, expand_graph, known_entities, max_vector_sim
        )
        metadata["trigger_reason"] = reason

        if should_run:
            metadata["stage3_triggered"] = True
            metadata["stages_run"].append("stage3_graph_expand")
            with timed_stage(timing, "stage3_graph_expand"):
                graph_results = self.graph_retrieval.retrieve(question, top_k=top_k, timing=TimingResult())

            seen_titles = {r.title for r in boosted_results}
            for gr in graph_results:
                if gr.title not in seen_titles:
                    top_score = max((r.score for r in boosted_results), default=0.5)
                    boosted_results.append(RetrievedItem(
                        title=gr.title,
                        content=gr.content,
                        doc_type=gr.doc_type,
                        score=round(top_score * 0.9, 4),
                        source="stage3_graph",
                        explanation=f"Stage 3: {gr.explanation}",
                    ))
                    seen_titles.add(gr.title)

            boosted_results.sort(key=lambda x: x.score, reverse=True)

        return boosted_results[:top_k], metadata
