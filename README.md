# GraphRAG Demo: Apache AGE + pgvector

A sample application showing how to combine graph traversal (Apache AGE) and vector similarity search (pgvector) in a single PostgreSQL instance for Retrieval-Augmented Generation.

Run one command. Ask a question. See three retrieval strategies compared side by side with performance metrics.

## Quick Start

```bash
# Clone and configure
cp .env.example .env
# Edit .env with your API key (ANTHROPIC_API_KEY or OPENAI_API_KEY)

# Start everything
docker compose up --build

# Open the demo
# http://localhost:8000
```

The database seeds automatically on first run (~160 documents about a fictional org called Acme Labs).

## What This Demonstrates

Every query runs three retrieval strategies in parallel:

| Strategy | How it works | Good at |
|----------|-------------|---------|
| **Vector-Only** | Embeds the question, cosine similarity search via pgvector | Finding semantically similar documents |
| **Graph-Only** | Extracts entities, traverses relationships via Apache AGE Cypher | Finding structurally connected information |
| **Graph+Vector** | Vector search seeds, graph expansion discovers related context, re-ranking combines both signals | Questions that need both semantic relevance and organizational context |

## Architecture

- **PostgreSQL 16** with `pgvector` (HNSW index) and `apache_age` (graph queries via Cypher)
- **FastAPI** orchestrator running all three strategies in parallel
- **Pluggable LLM** (Claude, OpenAI, Ollama) and embedding providers
- **Demo UI** with timing breakdown per strategy

## Configuration

Set in `.env`:

| Variable | Options | Default |
|----------|---------|---------|
| `LLM_PROVIDER` | `claude`, `openai`, `ollama` | `claude` |
| `EMBEDDING_PROVIDER` | `local`, `openai` | `local` |
| `ANTHROPIC_API_KEY` | Your key | - |
| `OPENAI_API_KEY` | Your key | - |
| `OLLAMA_BASE_URL` | URL | `http://host.docker.internal:11434` |

## Blog Series

This repo accompanies a three-part blog series:

1. [Why Vector Search Isn't Enough](blog/part1-why-vector-isnt-enough.md)
2. [Building a Graph-Aware RAG Pipeline](blog/part2-building-graph-rag.md)
3. [The Showdown](blog/part3-the-showdown.md)

## Project Structure

```
graphrag-demo/
├── docker-compose.yml          # Postgres + App
├── postgres/
│   ├── Dockerfile              # PG16 + AGE + pgvector from source
│   └── initdb/                 # SQL init scripts
├── app/
│   ├── main.py                 # FastAPI orchestrator
│   ├── retrieval/              # Three strategy implementations
│   ├── embeddings/             # Pluggable embedding providers
│   ├── llm/                    # Pluggable LLM providers
│   ├── seed/                   # Data generator + loader
│   └── static/                 # Demo UI
└── blog/                       # Tutorial blog posts
```
