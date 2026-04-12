from pydantic import BaseModel


class QueryRequest(BaseModel):
    question: str
    top_k: int = 10


class RetrievedItem(BaseModel):
    title: str
    content: str
    doc_type: str
    score: float
    source: str
    explanation: str


class StrategyResult(BaseModel):
    strategy: str
    results: list[RetrievedItem]
    answer: str
    timing: dict[str, float]
    metadata: dict | None = None


class QueryResponse(BaseModel):
    question: str
    strategies: list[StrategyResult]
