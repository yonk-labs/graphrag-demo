from models import RetrievedItem
from timing import TimingResult, timed_stage
from db import get_connection

# Cache for known entities (loaded once from the graph)
_known_entities: dict | None = None


def _load_known_entities(cur) -> dict:
    """Load all entity names from the graph for fuzzy matching."""
    global _known_entities
    if _known_entities is not None:
        return _known_entities

    entities = {
        "people": {}, "projects": {}, "services": {}, "teams": {}, "technologies": {},
        "cases": {}, "justices": {}, "issues": {},
    }

    for label, key in [
        ("Person", "people"),
        ("Project", "projects"),
        ("Service", "services"),
        ("Team", "teams"),
        ("Technology", "technologies"),
        ("Case", "cases"),
        ("Justice", "justices"),
        ("Issue", "issues"),
    ]:
        cur.execute(
            f"SELECT * FROM cypher('org_graph', $$ MATCH (n:{label}) RETURN n.id, n.name $$) "
            f"AS (id agtype, name agtype);"
        )
        for row in cur.fetchall():
            # AGE returns agtype with quotes, strip them
            node_id = str(row[0]).strip('"')
            name = str(row[1]).strip('"')
            entities[key][name.lower()] = node_id

    _known_entities = entities
    return entities


def extract_entities(question: str, known_entities: dict) -> list[tuple[str, str]]:
    """
    Match known entity names against the question text.
    Returns list of (Label, id) tuples.
    """
    q_lower = question.lower()
    matches = []

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

    for category, label in label_map.items():
        for name, entity_id in known_entities.get(category, {}).items():
            if name in q_lower:
                matches.append((label, entity_id))

    # Secondary match: last-name-only for justices
    for name, entity_id in known_entities.get("justices", {}).items():
        parts = name.split()
        if len(parts) > 1:
            last_name = parts[-1].lower()
            if last_name in q_lower and ("Justice", entity_id) not in matches:
                matches.append(("Justice", entity_id))

    return matches


def _traverse_from_entity(cur, label: str, entity_id: str, max_hops: int = 2) -> list[dict]:
    """Traverse the graph from a matched entity, collecting connected nodes and docs."""
    results = []

    # 1-hop: direct connections
    cur.execute(
        f"SELECT * FROM cypher('org_graph', $$ "
        f"MATCH (n:{label} {{id: '{entity_id}'}})-[r]->(m) "
        f"RETURN labels(m), m.id, m.name, type(r) "
        f"$$) AS (labels agtype, id agtype, name agtype, rel_type agtype);"
    )
    for row in cur.fetchall():
        results.append({
            "label": str(row[0]).strip('"[]'),
            "id": str(row[1]).strip('"'),
            "name": str(row[2]).strip('"'),
            "rel_type": str(row[3]).strip('"'),
            "hops": 1,
        })

    # Also check incoming edges
    cur.execute(
        f"SELECT * FROM cypher('org_graph', $$ "
        f"MATCH (m)-[r]->(n:{label} {{id: '{entity_id}'}}) "
        f"RETURN labels(m), m.id, m.name, type(r) "
        f"$$) AS (labels agtype, id agtype, name agtype, rel_type agtype);"
    )
    for row in cur.fetchall():
        results.append({
            "label": str(row[0]).strip('"[]'),
            "id": str(row[1]).strip('"'),
            "name": str(row[2]).strip('"'),
            "rel_type": str(row[3]).strip('"'),
            "hops": 1,
        })

    if max_hops >= 2:
        # 2-hop: connections of connections
        cur.execute(
            f"SELECT * FROM cypher('org_graph', $$ "
            f"MATCH (n:{label} {{id: '{entity_id}'}})-[]->(m)-[r2]->(o) "
            f"WHERE o <> n "
            f"RETURN labels(o), o.id, o.name, type(r2) "
            f"$$) AS (labels agtype, id agtype, name agtype, rel_type agtype);"
        )
        for row in cur.fetchall():
            results.append({
                "label": str(row[0]).strip('"[]'),
                "id": str(row[1]).strip('"'),
                "name": str(row[2]).strip('"'),
                "rel_type": str(row[3]).strip('"'),
                "hops": 2,
            })

    return results


def _fetch_docs_for_entities(cur, entity_ids: list[str]) -> list[tuple]:
    """Fetch documents authored by or related to the given entity IDs, newest first."""
    if not entity_ids:
        return []

    placeholders = ",".join(["%s"] * len(entity_ids))
    cur.execute(
        f"SELECT title, content, doc_type, author_id, project_id "
        f"FROM documents "
        f"WHERE author_id IN ({placeholders}) OR project_id IN ({placeholders}) "
        f"ORDER BY created_at DESC",
        entity_ids + entity_ids,
    )
    return cur.fetchall()


class GraphRetrieval:
    def retrieve(
        self, question: str, top_k: int, timing: TimingResult
    ) -> list[RetrievedItem]:
        with get_connection() as conn:
            with conn.cursor() as cur:
                # Stage 1: Extract entities from question
                with timed_stage(timing, "entity_extraction"):
                    known = _load_known_entities(cur)
                    matched = extract_entities(question, known)

                if not matched:
                    timing.add("graph_traversal", 0.0)
                    return []

                # Stage 2: Traverse graph from matched entities; track hop distance
                with timed_stage(timing, "graph_traversal"):
                    all_graph_nodes = []
                    for label, entity_id in matched:
                        nodes = _traverse_from_entity(cur, label, entity_id)
                        all_graph_nodes.extend(nodes)

                    # Track per-entity minimum hop (1 vs 2)
                    entity_hops: dict[str, int] = {}
                    for node in all_graph_nodes:
                        eid = node["id"]
                        hops = node["hops"]
                        if eid not in entity_hops or hops < entity_hops[eid]:
                            entity_hops[eid] = hops

                    # Originally matched entities are hop 0 (treat as 1-hop for scoring)
                    for _label, eid in matched:
                        entity_hops[eid] = 0

                    all_entity_ids = list(entity_hops.keys())
                    doc_rows = _fetch_docs_for_entities(cur, all_entity_ids)

        # Build results with relevance-weighted scores
        results = []
        seen_titles = set()
        for row in doc_rows:
            title = row[0]
            if title in seen_titles:
                continue
            seen_titles.add(title)

            author_id = row[3]
            project_id = row[4]
            doc_type = row[2]

            # Minimum hop distance for this doc's key entities
            hops_candidates = []
            if author_id in entity_hops:
                hops_candidates.append(entity_hops[author_id])
            if project_id in entity_hops:
                hops_candidates.append(entity_hops[project_id])
            min_hops = min(hops_candidates) if hops_candidates else 2

            # 0 or 1 hop = strong signal; 2-hop = weaker
            if min_hops <= 1:
                score = 0.9
            else:
                score = 0.5

            # Prefer authoritative doc types
            if doc_type in ("architecture_doc", "decision_record"):
                score += 0.1

            score = min(score, 1.0)

            entity_names = [f"{l}:{eid}" for l, eid in matched]
            explanation = (
                f"Found via graph traversal from {', '.join(entity_names)} "
                f"({min_hops}-hop)"
            )

            results.append(RetrievedItem(
                title=title,
                content=row[1],
                doc_type=doc_type,
                score=round(score, 4),
                source="graph",
                explanation=explanation,
            ))

        # Sort by score, take top_k
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]
