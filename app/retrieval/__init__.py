from typing import Protocol

from models import RetrievedItem
from timing import TimingResult


class RetrievalStrategy(Protocol):
    def retrieve(
        self, question: str, top_k: int, timing: TimingResult
    ) -> list[RetrievedItem]: ...
