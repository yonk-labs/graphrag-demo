import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

from config import settings
from db import init_pool, close_pool
from models import QueryRequest, QueryResponse, StrategyResult
from timing import TimingResult
from embeddings import get_embedding_provider
from llm import get_llm_provider
from retrieval.vector import VectorRetrieval
from retrieval.graph import GraphRetrieval
from retrieval.hybrid import HybridRetrieval
from retrieval.combined import CombinedRetrieval
from retrieval.production import ProductionRetrieval
from seed.seed import main as run_seed

_executor = ThreadPoolExecutor(max_workers=8)
_embedding_provider = None
_llm_provider = None
_vector_retrieval = None
_graph_retrieval = None
_hybrid_retrieval = None
_combined_retrieval = None
_production_retrieval = None


EXAMPLE_QUERIES = [
    {
        "question": "What was decided about the billing migration?",
        "description": "Stage 1+2 sufficient (semantic lookup, no graph expand)",
        "dataset": "acme",
    },
    {
        "question": "Who should I talk to about the payment service?",
        "description": "Stage 3 triggers (graph-shaped 'who' pattern)",
        "dataset": "acme",
    },
    {
        "question": "What's the blast radius if the auth service goes down?",
        "description": "Stage 3 triggers (dependency chain)",
        "dataset": "acme",
    },
    {
        "question": "Find cases about administrative overreach",
        "description": "Stage 1+2 sufficient (semantic topical search)",
        "dataset": "scotus",
    },
    {
        "question": "Which cases did Justice Thomas and Justice Sotomayor vote on together?",
        "description": "Stage 3 triggers (multi-entity multi-hop)",
        "dataset": "scotus",
    },
    {
        "question": "What First Amendment cases did Justice Sotomayor vote on?",
        "description": "Stage 3 triggers (justice + issue intersection)",
        "dataset": "scotus",
    },
    {
        "question": "Find cases with docket number 17-204",
        "description": "Stage 1+2 sufficient (exact keyword match via BM25)",
        "dataset": "scotus",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _embedding_provider, _llm_provider
    global _vector_retrieval, _graph_retrieval, _hybrid_retrieval, _combined_retrieval, _production_retrieval

    init_pool()

    # Auto-seed on first run (no-op if already seeded)
    try:
        run_seed()
    except Exception as e:
        print(f"Seed skipped or failed: {e}")

    _embedding_provider = get_embedding_provider(settings.embedding_provider)
    _llm_provider = get_llm_provider(settings.llm_provider)
    _vector_retrieval = VectorRetrieval(_embedding_provider)
    _graph_retrieval = GraphRetrieval()
    _hybrid_retrieval = HybridRetrieval(_embedding_provider)
    _combined_retrieval = CombinedRetrieval(
        vector_retrieval=VectorRetrieval(_embedding_provider),
        graph_retrieval=GraphRetrieval(),
        hybrid_retrieval=HybridRetrieval(_embedding_provider),
    )
    _production_retrieval = ProductionRetrieval(
        hybrid_retrieval=HybridRetrieval(_embedding_provider),
        graph_retrieval=GraphRetrieval(),
    )

    # Pre-warm the Stage 2 neighbor cache so the first real query isn't stuck
    # behind a full graph scan. Failures are non-fatal (first query will warm).
    try:
        from retrieval.production import _warm_neighbor_cache_for_label
        from db import get_connection as _get_conn
        _label_pairs = [
            ("Person", "people"), ("Project", "projects"), ("Service", "services"),
            ("Team", "teams"), ("Technology", "technologies"),
            ("Case", "cases"), ("Justice", "justices"), ("Issue", "issues"),
        ]
        with _get_conn() as _conn:
            with _conn.cursor() as _cur:
                for _label, _cat in _label_pairs:
                    _warm_neighbor_cache_for_label(_cur, _label, _cat)
    except Exception as _e:
        print(f"Stage 2 cache warm skipped: {_e}")

    yield
    close_pool()


app = FastAPI(title="GraphRAG Demo", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _run_strategy(name: str, question: str, top_k: int) -> dict:
    """Run a retrieval strategy and generate an LLM answer. Runs in thread pool."""
    timing = TimingResult()
    production_metadata = None

    if name == "vector":
        results = _vector_retrieval.retrieve(question, top_k, timing)
    elif name == "hybrid":
        results = _hybrid_retrieval.retrieve(question, top_k, timing)
    elif name == "graph":
        results = _graph_retrieval.retrieve(question, top_k, timing)
    elif name == "production":
        results, production_metadata = _production_retrieval.retrieve(question, top_k, timing)
    else:
        return {"strategy": name, "results": [], "answer": "Unknown strategy", "timing": {}, "metadata": None}

    # Generate LLM answer from retrieved context
    from timing import timed_stage
    context = [f"[{r.doc_type}] {r.title}\n{r.content}" for r in results[:5]]
    with timed_stage(timing, "llm_generation"):
        if not context:
            answer = "No relevant documents found for this query."
        else:
            try:
                answer = _llm_provider.generate(question, context)
            except Exception as e:
                answer = (
                    f"[LLM generation unavailable: {type(e).__name__}] "
                    f"Retrieved {len(results)} documents. "
                    f"Set ANTHROPIC_API_KEY or OPENAI_API_KEY to enable generated answers."
                )

    return {
        "strategy": name,
        "results": [r.model_dump() for r in results],
        "answer": answer,
        "timing": timing.to_dict(),
        "metadata": production_metadata if name == "production" else None,
    }


@app.get("/")
def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.post("/api/query")
async def query(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    loop = asyncio.get_event_loop()

    # Run all four strategies in parallel
    vector_future = loop.run_in_executor(
        _executor, _run_strategy, "vector", request.question, request.top_k
    )
    hybrid_future = loop.run_in_executor(
        _executor, _run_strategy, "hybrid", request.question, request.top_k
    )
    graph_future = loop.run_in_executor(
        _executor, _run_strategy, "graph", request.question, request.top_k
    )
    production_future = loop.run_in_executor(
        _executor, _run_strategy, "production", request.question, request.top_k
    )

    results = await asyncio.gather(vector_future, hybrid_future, graph_future, production_future)

    return QueryResponse(
        question=request.question,
        strategies=[StrategyResult(**r) for r in results],
    )


@app.get("/api/examples")
def examples():
    return EXAMPLE_QUERIES


@app.get("/health")
def health():
    return {"status": "ok"}
