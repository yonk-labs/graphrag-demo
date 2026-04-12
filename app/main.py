import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import settings
from db import init_pool, close_pool
from models import QueryRequest, QueryResponse, StrategyResult
from timing import TimingResult
from embeddings import get_embedding_provider
from llm import get_llm_provider
from retrieval.vector import VectorRetrieval
from retrieval.graph import GraphRetrieval
from retrieval.combined import CombinedRetrieval
from seed.seed import main as run_seed

_executor = ThreadPoolExecutor(max_workers=6)
_embedding_provider = None
_llm_provider = None
_vector_retrieval = None
_graph_retrieval = None
_combined_retrieval = None


EXAMPLE_QUERIES = [
    {
        "question": "What was decided about the billing migration?",
        "description": "Vector excels: finds the decision doc by semantic match",
    },
    {
        "question": "Who should I talk to about the payment service?",
        "description": "Graph excels: finds the ownership chain",
    },
    {
        "question": "What's the blast radius if the auth service goes down?",
        "description": "Combined wins: dependency chain + related incidents + responsible people",
    },
    {
        "question": "Catch me up on what the data team has been working on",
        "description": "Combined wins: team projects + recent docs + cross-team impacts",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _embedding_provider, _llm_provider
    global _vector_retrieval, _graph_retrieval, _combined_retrieval

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
    _combined_retrieval = CombinedRetrieval(
        vector_retrieval=VectorRetrieval(_embedding_provider),
    )
    yield
    close_pool()


app = FastAPI(title="GraphRAG Demo", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")


def _run_strategy(name: str, question: str, top_k: int) -> dict:
    """Run a retrieval strategy and generate an LLM answer. Runs in thread pool."""
    timing = TimingResult()

    if name == "vector":
        results = _vector_retrieval.retrieve(question, top_k, timing)
    elif name == "graph":
        results = _graph_retrieval.retrieve(question, top_k, timing)
    elif name == "graph+vector":
        results = _combined_retrieval.retrieve(question, top_k, timing)
    else:
        return {"strategy": name, "results": [], "answer": "Unknown strategy", "timing": {}}

    # Generate LLM answer from retrieved context
    from timing import timed_stage
    context = [f"[{r.doc_type}] {r.title}\n{r.content}" for r in results[:5]]
    with timed_stage(timing, "llm_generation"):
        if context:
            answer = _llm_provider.generate(question, context)
        else:
            answer = "No relevant documents found for this query."

    return {
        "strategy": name,
        "results": [r.model_dump() for r in results],
        "answer": answer,
        "timing": timing.to_dict(),
    }


@app.get("/")
def root():
    return FileResponse("static/index.html")


@app.post("/api/query")
async def query(request: QueryRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    loop = asyncio.get_event_loop()

    # Run all three strategies in parallel
    vector_future = loop.run_in_executor(
        _executor, _run_strategy, "vector", request.question, request.top_k
    )
    graph_future = loop.run_in_executor(
        _executor, _run_strategy, "graph", request.question, request.top_k
    )
    combined_future = loop.run_in_executor(
        _executor, _run_strategy, "graph+vector", request.question, request.top_k
    )

    results = await asyncio.gather(vector_future, graph_future, combined_future)

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
