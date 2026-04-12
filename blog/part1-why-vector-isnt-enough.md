# Why Vector Search Isn't Enough

Your RAG pipeline is returning technically correct, completely useless answers. Somebody on your team asks, "Who should I talk to about the payment service?" and gets back a two-year-old meeting note where Karen from marketing mentioned that her credit card was declined at lunch. Technically, that doc contains the word "payment." Technically, the retriever did its job. Practically, you just made it harder for a human to get their work done, and now they're back in Slack asking the same question the old-fashioned way.

I've been doing databases for about 20 years, and I've watched this exact failure mode show up in every single production RAG system I've poked at in the last eighteen months. It's not a bug. It's not a bad embedding model. It's not even a chunking problem (though your chunking is probably also bad, sorry). It's that vector search is answering a fundamentally different question than the one your users are asking. And until we get honest about that, we're going to keep shipping demos that look great on stage and fall over the first time someone tries to use them for real work.

## The problem with vector-only RAG

Here's the deal. Vector search finds text that sounds like your question. That's it. That's the whole trick. You embed the question, you embed a pile of documents, you cosine-similarity your way to the top K. It's elegant, it's fast, it's genuinely useful for a lot of things. Summarizing a long doc? Great. Finding that one blog post you half-remember reading? Great. Pulling the relevant paragraph out of a 400-page PDF? Also great.

But organizations have structure that isn't written down anywhere in document text. Who reports to whom. Which team owns which service. Which project depends on which other project. Who knows the history of that one weird Kafka cluster that nobody wants to touch. That stuff lives in org charts, in service catalogs, in people's heads, and occasionally in a Confluence page that hasn't been updated since 2022. It does not live in the text of meeting notes in a way a cosine similarity score can find.

So when someone asks, "What's the blast radius if the auth service goes down?" what they actually need is: find the auth service, walk to every service that depends on it, walk to every project those services belong to, find the owners, find the on-call rotations. That's a graph traversal. Three or four hops. Vector search, no matter how good your embeddings are, cannot do this. You can throw GPT-5 at the output all day long and it will not magically reconstruct a dependency chain that was never in any single document.

And look, I'm not here to trash vector search. I love pgvector. I use it constantly. I'm saying that we've collectively convinced ourselves that stuffing everything into an embedding is the answer, when for a whole class of questions, the honest answer is: you're using the wrong tool. It's like trying to find your car keys with a metal detector set to "gold." The tool is fine. The tool is not the problem.

## The fix preview

What if your retrieval layer could search by meaning AND walk a knowledge graph in the same query, against the same database, with the same backup strategy and the same operational team? Turns out you can. Same Postgres, two extensions: pgvector for the embeddings, Apache AGE for the graph. No new database to run. No new pager rotation. No shiny vendor demo where the salesperson just happens to skip the part about HA.

## What is Apache AGE?

Apache AGE is a PostgreSQL extension that adds graph database capabilities on top of regular Postgres. You create a graph, you define vertex labels and edge labels, and then you write Cypher queries (yes, the same Cypher that Neo4j uses) directly inside a SQL statement. Nodes and edges are first-class objects, not JSON blobs you're pretending are a graph. It supports multi-hop traversals, pattern matching, variable-length paths, all the stuff you'd expect from a real graph engine.

Nothing about it is magic. It's a well-designed extension that leans on the Postgres storage engine, transaction model, and backup tooling you already know. Which, if you've ever tried to run a standalone graph database in production next to your primary transactional store, is the whole point. The hard problem in AI Land is always data engineering, not database selection. AGE gives you graph power without forcing you to become a graph database administrator on top of everything else.

## What is pgvector?

You probably already know this one. pgvector is the Postgres extension for storing and searching vector embeddings, with HNSW indexes, cosine distance, inner product, the works. Standard tool at this point. If you're doing anything with LLMs and Postgres, you're already using it or you're about to.

## Setup: actual working code

Here's the fun part. I'm not going to hand-wave this. The repo for this series is real, the code runs, and if it doesn't, please open an issue and roast me publicly.

There's no reliable pre-built Postgres image that ships with both pgvector and Apache AGE, so we build from source. It's not as scary as it sounds. Here's the Dockerfile:

```dockerfile
FROM postgres:16

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    postgresql-server-dev-16 \
    libreadline-dev \
    zlib1g-dev \
    flex \
    bison \
    && rm -rf /var/lib/apt/lists/*

# Build and install pgvector 0.8.0
RUN git clone --branch v0.8.0 --depth 1 https://github.com/pgvector/pgvector.git /tmp/pgvector \
    && cd /tmp/pgvector \
    && make OPTFLAGS="" \
    && make install \
    && rm -rf /tmp/pgvector

# Build and install Apache AGE 1.5.0 for PG16
RUN git clone --branch PG16/v1.5.0 --depth 1 https://github.com/apache/age.git /tmp/age \
    && cd /tmp/age \
    && make install \
    && rm -rf /tmp/age

# Preload AGE so LOAD is not needed per-session
RUN echo "shared_preload_libraries = 'age'" >> /usr/share/postgresql/postgresql.conf.sample

COPY initdb/ /docker-entrypoint-initdb.d/
```

Two things worth calling out. First, AGE needs to be in `shared_preload_libraries` so you don't have to `LOAD 'age'` at the start of every session. This was my first face-plant when I started with AGE. I spent an embarrassing amount of time wondering why my Cypher queries "randomly" stopped working between sessions. It's because I didn't read the docs. Classic Yonk move.

Second, we pin specific versions: pgvector 0.8.0 and AGE 1.5.0 for Postgres 16. Pin your versions. Don't get cute with "latest." Future you will thank present you.

The init scripts in `initdb/` run automatically the first time the container spins up a fresh data volume. The first one turns on both extensions:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS age;
ALTER DATABASE graphrag SET search_path = ag_catalog, "$user", public;
```

That `search_path` line matters. AGE puts its functions in `ag_catalog`, and you want them visible without qualifying every call. Next, the relational schema for documents and their embeddings:

```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    doc_type TEXT NOT NULL CHECK (doc_type IN (
        'meeting_note', 'architecture_doc', 'incident_report', 'decision_record'
    )),
    author_id TEXT NOT NULL,
    project_id TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    embedding vector(384)
);

CREATE INDEX idx_documents_embedding ON documents
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 200);
```

384-dimensional vectors because we're using a small, local embedding model for the demo (right-sized AI, remember, you do not need OpenAI's biggest embedding model to search 160 documents). HNSW index for fast approximate nearest neighbor. Standard pgvector stuff.

Then the graph schema, which is where things get interesting:

```sql
SELECT ag_catalog.create_graph('org_graph');

SELECT ag_catalog.create_vlabel('org_graph', 'Person');
SELECT ag_catalog.create_vlabel('org_graph', 'Team');
SELECT ag_catalog.create_vlabel('org_graph', 'Project');
SELECT ag_catalog.create_vlabel('org_graph', 'Service');
SELECT ag_catalog.create_vlabel('org_graph', 'Technology');

SELECT ag_catalog.create_elabel('org_graph', 'WORKS_ON');
SELECT ag_catalog.create_elabel('org_graph', 'MEMBER_OF');
SELECT ag_catalog.create_elabel('org_graph', 'DEPENDS_ON');
SELECT ag_catalog.create_elabel('org_graph', 'OWNS');
SELECT ag_catalog.create_elabel('org_graph', 'KNOWS_ABOUT');
SELECT ag_catalog.create_elabel('org_graph', 'REPORTS_TO');
SELECT ag_catalog.create_elabel('org_graph', 'AUTHORED');
```

Five vertex types, seven edge types. People, teams, projects, services, technologies. They work on things, they're members of things, they own things, they depend on things. This is the structure your documents are *about* but never actually *contain*.

The `docker-compose.yml` wires it together with a Python app that we'll actually use in Part 2:

```yaml
services:
  postgres:
    build:
      context: ./postgres
    environment:
      POSTGRES_DB: graphrag
      POSTGRES_USER: graphrag
      POSTGRES_PASSWORD: graphrag
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U graphrag -d graphrag"]
      interval: 5s
      timeout: 5s
      retries: 10
```

Bring it up with `docker compose up --build`. First run takes a few minutes because we're compiling two extensions from source. Grab a coffee. After that, subsequent builds are cached and fast. You can verify the extensions are loaded with `\dx` in psql, and you can confirm the graph exists with `SELECT * FROM ag_catalog.ag_graph;`.

## Loading the data

The seed script auto-runs on startup and populates a fictional organization called Acme Labs: 15 people, 8 projects, 5 services, 160 documents across meeting notes, architecture docs, incident reports, and decision records. All the relationships between people and teams and projects are wired up in the graph. I'll spare you the details here because the point of this post is the *why*, not the *what*, and Part 2 is where we actually start running queries against both stores together.

## First demo: where vector search falls flat

Fire up the demo app and ask it, vector-only, "Who should I talk to about the payment service?" You'll get back a ranked list of documents that mention payments. A meeting note where somebody complained about Stripe latency. An architecture doc that references the payment API in passing. An incident report from a Black Friday outage. None of them tell you who actually owns the service today.

And that's because the answer isn't written down in any one document. The answer is a graph walk: find the Service node named "payment-service," follow the OWNS edge backward to the Team, follow MEMBER_OF to the People, maybe follow REPORTS_TO one hop up for a tech lead. Vector search can't do this, not because pgvector is bad, but because the information literally isn't in the text corpus in the form vector search needs. You cannot cosine-similarity your way to a relationship that was never serialized into prose.

## What's next

In Part 2, we add the graph layer for real and build three different retrieval strategies: pure vector, pure graph, and a hybrid that does both and combines the results. I'll show you the exact Cypher queries, the exact SQL, and the exact moments where one approach beats the other. I'll also show you at least one query where the hybrid is worse than either component alone, because that happens too, and if your blog series never shows you the failure cases, you're reading marketing, not engineering.

Before you read Part 2, do me a favor. Go open your own RAG system and ask it three questions that require following a chain of relationships. Not "summarize this," not "find the doc about X." Real questions like, "If this service goes down, who gets paged, and what breaks?" Write down what you get back. Then ask yourself honestly: is this the answer, or is it just text that sounds like the answer? If you can tell the difference, you already get why we're building this. If you can't, you're about to find out.

See you in Part 2.
