import time
from collections.abc import Callable
from typing import Any


class TimingMixin:
    def time_it(self, operation: Callable[[], Any]) -> tuple[Any, float]:
        start = time.perf_counter()
        result = operation()
        duration_ms = (time.perf_counter() - start) * 1000
        return result, duration_ms
