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
            """INSERT INTO documents (id, title, content, doc_type, author_id, project_id, created_at, embedding)
               VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s::vector)""",
            (
                doc["title"],
                doc["content"],
                doc["doc_type"],
                doc["author_id"],
                doc["project_id"],
                doc["created_at"],
                str(embedding),
            ),
        )


def check_already_seeded(cur) -> bool:
    """Check if data has already been loaded."""
    cur.execute("SELECT COUNT(*) FROM documents;")
    count = cur.fetchone()[0]
    return count > 0


def main():
    print("Connecting to database...")
    conn = psycopg2.connect(settings.database_url)
    conn.autocommit = True

    with conn.cursor() as cur:
        cur.execute("SET search_path = ag_catalog, public;")
        cur.execute("LOAD 'age';")

        if check_already_seeded(cur):
            print("Database already seeded. Skipping.")
            conn.close()
            return

        print("Generating org data...")
        data = generate_all()

        load_graph(cur, data)
        print(f"Graph loaded: {len(data['people'])} people, "
              f"{len(data['teams'])} teams, {len(data['projects'])} projects, "
              f"{len(data['services'])} services, {len(data['technologies'])} technologies")

        embedding_provider = get_embedding_provider(settings.embedding_provider)
        load_documents(cur, data, embedding_provider)
        print(f"Documents loaded: {len(data['documents'])} documents with embeddings")

    conn.close()
    print("Seed complete!")


if __name__ == "__main__":
    main()
