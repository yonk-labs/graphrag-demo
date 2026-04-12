"""
Loads generated data into Postgres: graph nodes/edges into AGE,
documents with embeddings into the documents table.
"""

import json
import sys
import os

import psycopg2

# Add parent dir so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from embeddings import get_embedding_provider
from seed.generate_data import generate_all
from seed.scotus_data import generate_all as generate_scotus_all


def _cypher(cur, query: str):
    """Execute a Cypher query via AGE."""
    cur.execute(
        f"SELECT * FROM cypher('org_graph', $$ {query} $$) AS (result agtype);"
    )


def _escape(val: str) -> str:
    """Escape single quotes for Cypher string literals."""
    return val.replace("\\", "\\\\").replace("'", "\\'")


def load_graph(cur, data: dict):
    """Load all nodes and edges into the AGE graph."""
    print("Loading graph nodes...")

    # Vertex: People
    for p in data["people"]:
        _cypher(cur, (
            f"CREATE (n:Person {{"
            f"id: '{_escape(p['id'])}', "
            f"name: '{_escape(p['name'])}', "
            f"title: '{_escape(p['title'])}', "
            f"email: '{_escape(p['email'])}', "
            f"team_id: '{_escape(p['team_id'])}'"
            f"}})"
        ))

    # Vertex: Teams
    for t in data["teams"]:
        _cypher(cur, (
            f"CREATE (n:Team {{"
            f"id: '{_escape(t['id'])}', "
            f"name: '{_escape(t['name'])}', "
            f"department: '{_escape(t['department'])}'"
            f"}})"
        ))

    # Vertex: Projects
    for p in data["projects"]:
        _cypher(cur, (
            f"CREATE (n:Project {{"
            f"id: '{_escape(p['id'])}', "
            f"name: '{_escape(p['name'])}', "
            f"description: '{_escape(p['description'])}', "
            f"status: '{_escape(p['status'])}'"
            f"}})"
        ))

    # Vertex: Services
    for s in data["services"]:
        _cypher(cur, (
            f"CREATE (n:Service {{"
            f"id: '{_escape(s['id'])}', "
            f"name: '{_escape(s['name'])}', "
            f"description: '{_escape(s['description'])}', "
            f"tier: '{_escape(s['tier'])}'"
            f"}})"
        ))

    # Vertex: Technologies
    for t in data["technologies"]:
        _cypher(cur, (
            f"CREATE (n:Technology {{"
            f"id: '{_escape(t['id'])}', "
            f"name: '{_escape(t['name'])}', "
            f"category: '{_escape(t['category'])}'"
            f"}})"
        ))

    print("Loading graph edges...")
    rels = data["relationships"]

    # MEMBER_OF (derived from people's team_id)
    for p in data["people"]:
        _cypher(cur, (
            f"MATCH (a:Person {{id: '{_escape(p['id'])}'}}), "
            f"(b:Team {{id: '{_escape(p['team_id'])}'}}) "
            f"CREATE (a)-[:MEMBER_OF {{role: '{_escape(p['title'])}'}}]->(b)"
        ))

    # WORKS_ON
    for r in rels["works_on"]:
        _cypher(cur, (
            f"MATCH (a:Person {{id: '{_escape(r['person_id'])}'}}), "
            f"(b:Project {{id: '{_escape(r['project_id'])}'}}) "
            f"CREATE (a)-[:WORKS_ON {{role: '{_escape(r['role'])}'}}]->(b)"
        ))

    # REPORTS_TO
    for r in rels["reports_to"]:
        _cypher(cur, (
            f"MATCH (a:Person {{id: '{_escape(r['person_id'])}'}}), "
            f"(b:Person {{id: '{_escape(r['manager_id'])}'}}) "
            f"CREATE (a)-[:REPORTS_TO]->(b)"
        ))

    # OWNS
    for r in rels["owns"]:
        _cypher(cur, (
            f"MATCH (a:Team {{id: '{_escape(r['team_id'])}'}}), "
            f"(b:Service {{id: '{_escape(r['service_id'])}'}}) "
            f"CREATE (a)-[:OWNS]->(b)"
        ))

    # DEPENDS_ON
    for r in rels["depends_on"]:
        # Source can be a Project or Service
        for label in ["Project", "Service"]:
            _cypher(cur, (
                f"MATCH (a:{label} {{id: '{_escape(r['source_id'])}'}}), "
                f"(b:Service {{id: '{_escape(r['target_id'])}'}}) "
                f"CREATE (a)-[:DEPENDS_ON {{dependency_type: '{_escape(r['dependency_type'])}'}}]->(b)"
            ))

    # KNOWS_ABOUT
    for r in rels["knows_about"]:
        _cypher(cur, (
            f"MATCH (a:Person {{id: '{_escape(r['person_id'])}'}}), "
            f"(b:Technology {{id: '{_escape(r['tech_id'])}'}}) "
            f"CREATE (a)-[:KNOWS_ABOUT {{proficiency: '{_escape(r['proficiency'])}'}}]->(b)"
        ))

    # AUTHORED (from documents)
    for doc in data["documents"]:
        _cypher(cur, (
            f"MATCH (a:Person {{id: '{_escape(doc['author_id'])}'}}) "
            f"CREATE (a)-[:AUTHORED {{doc_id: '{_escape(doc['id'])}'}}]->(a)"
        ))


def load_documents(cur, data: dict, embedding_provider):
    """Load documents with embeddings into the documents table."""
    print("Computing embeddings (this may take a minute)...")
    docs = data["documents"]

    # Batch embed all document contents
    contents = [d["content"] for d in docs]
    embeddings = embedding_provider.embed_batch(contents)

    print(f"Loading {len(docs)} documents...")
    for doc, embedding in zip(docs, embeddings):
        cur.execute(
            """INSERT INTO documents (id, title, content, doc_type, author_id, project_id, dataset, created_at, embedding)
               VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s::vector)""",
            (
                doc["title"],
                doc["content"],
                doc["doc_type"],
                doc["author_id"],
                doc["project_id"],
                doc.get("dataset", "acme"),
                doc["created_at"],
                str(embedding),
            ),
        )


def load_scotus_graph(cur, data: dict):
    """Load SCOTUS nodes and edges into the AGE graph."""
    print("Loading SCOTUS graph nodes...")

    for j in data["justices"]:
        first_term = j.get("first_term") if j.get("first_term") is not None else 2018
        last_term = j.get("last_term") if j.get("last_term") is not None else 2023
        _cypher(cur, (
            f"CREATE (n:Justice {{"
            f"id: '{_escape(j['id'])}', "
            f"name: '{_escape(j['name'])}', "
            f"first_term: {first_term}, "
            f"last_term: {last_term}"
            f"}})"
        ))

    for iss in data["issues"]:
        _cypher(cur, (
            f"CREATE (n:Issue {{"
            f"id: '{_escape(iss['id'])}', "
            f"name: '{_escape(iss['name'])}', "
            f"category: '{_escape(iss['category'])}'"
            f"}})"
        ))

    for c in data["cases"]:
        term_val = c["term"] if c["term"] is not None else 2020
        _cypher(cur, (
            f"CREATE (n:Case {{"
            f"id: '{_escape(c['id'])}', "
            f"name: '{_escape(c['name'])}', "
            f"docket: '{_escape(c['docket'])}', "
            f"citation: '{_escape(c['citation'])}', "
            f"term: {term_val}, "
            f"petitioner: '{_escape(c['petitioner'])}', "
            f"respondent: '{_escape(c['respondent'])}', "
            f"vote_split: '{_escape(c['vote_split'])}', "
            f"winning_party: '{_escape(c['winning_party'])}'"
            f"}})"
        ))

    print("Loading SCOTUS graph edges...")

    # CONCERNS: Case -> Issue
    for c in data["cases"]:
        for iid in c["issue_ids"]:
            _cypher(cur, (
                f"MATCH (a:Case {{id: '{_escape(c['id'])}'}}), "
                f"(b:Issue {{id: '{_escape(iid)}'}}) "
                f"CREATE (a)-[:CONCERNS]->(b)"
            ))

    # Votes: VOTED_MAJORITY / VOTED_DISSENT / VOTED_CONCURRING
    for c in data["cases"]:
        for vote in c["votes"]:
            jid = vote["justice_id"]
            side = vote["side"]
            role = (vote.get("role") or "").lower()
            edge = "VOTED_MAJORITY" if side == "majority" else "VOTED_DISSENT"
            _cypher(cur, (
                f"MATCH (a:Justice {{id: '{_escape(jid)}'}}), "
                f"(b:Case {{id: '{_escape(c['id'])}'}}) "
                f"CREATE (a)-[:{edge}]->(b)"
            ))
            if "concurring" in role or "concurrence" in role:
                _cypher(cur, (
                    f"MATCH (a:Justice {{id: '{_escape(jid)}'}}), "
                    f"(b:Case {{id: '{_escape(c['id'])}'}}) "
                    f"CREATE (a)-[:VOTED_CONCURRING]->(b)"
                ))

    # WROTE_OPINION (majority author and dissent authors)
    for c in data["cases"]:
        if c.get("majority_author_id"):
            _cypher(cur, (
                f"MATCH (a:Justice {{id: '{_escape(c['majority_author_id'])}'}}), "
                f"(b:Case {{id: '{_escape(c['id'])}'}}) "
                f"CREATE (a)-[:WROTE_OPINION {{type: 'majority'}}]->(b)"
            ))
        for did in c.get("dissent_author_ids", []):
            _cypher(cur, (
                f"MATCH (a:Justice {{id: '{_escape(did)}'}}), "
                f"(b:Case {{id: '{_escape(c['id'])}'}}) "
                f"CREATE (a)-[:WROTE_OPINION {{type: 'dissent'}}]->(b)"
            ))

    # CITED: Case -> Case
    for cit in data["citations"]:
        _cypher(cur, (
            f"MATCH (a:Case {{id: '{_escape(cit['from_id'])}'}}), "
            f"(b:Case {{id: '{_escape(cit['to_id'])}'}}) "
            f"CREATE (a)-[:CITED]->(b)"
        ))


def _dataset_seeded(cur, dataset: str) -> bool:
    cur.execute("SELECT COUNT(*) FROM documents WHERE dataset = %s;", (dataset,))
    return cur.fetchone()[0] > 0


def main():
    print("Connecting to database...")
    conn = psycopg2.connect(settings.database_url)
    conn.autocommit = True

    with conn.cursor() as cur:
        cur.execute("SET search_path = ag_catalog, public;")
        cur.execute("LOAD 'age';")

        embedding_provider = None

        if not _dataset_seeded(cur, "acme"):
            print("Generating Acme org data...")
            data = generate_all()
            load_graph(cur, data)
            print(f"Acme graph loaded: {len(data['people'])} people, "
                  f"{len(data['teams'])} teams, {len(data['projects'])} projects, "
                  f"{len(data['services'])} services, {len(data['technologies'])} technologies")
            embedding_provider = get_embedding_provider(settings.embedding_provider)
            load_documents(cur, data, embedding_provider)
            print(f"Acme documents loaded: {len(data['documents'])} documents with embeddings")
        else:
            print("Acme already seeded. Skipping.")

        if not _dataset_seeded(cur, "scotus"):
            print("Parsing SCOTUS case files...")
            scotus_data = generate_scotus_all()
            load_scotus_graph(cur, scotus_data)
            print(
                f"SCOTUS graph loaded: {len(scotus_data['cases'])} cases, "
                f"{len(scotus_data['justices'])} justices, "
                f"{len(scotus_data['issues'])} issues, "
                f"{len(scotus_data['citations'])} citations"
            )
            if embedding_provider is None:
                embedding_provider = get_embedding_provider(settings.embedding_provider)
            load_documents(cur, scotus_data, embedding_provider)
            print(f"SCOTUS documents loaded: {len(scotus_data['documents'])} documents with embeddings")
        else:
            print("SCOTUS already seeded. Skipping.")

    conn.close()
    print("Seed complete!")


if __name__ == "__main__":
    main()
