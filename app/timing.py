import time
from contextlib import contextmanager


class TimingResult:
    def __init__(self):
        self.stages: dict[str, float] = {}

    def add(self, name: str, ms: float):
        self.stages[name] = ms

    @property
    def total_ms(self) -> float:
        return sum(self.stages.values())

    def to_dict(self) -> dict:
        return {**self.stages, "total": self.total_ms}


@contextmanager
def timed_stage(timing: TimingResult, name: str):
    start = time.perf_counter()
    yield
    elapsed = (time.perf_counter() - start) * 1000
    timing.add(name, round(elapsed, 2))
