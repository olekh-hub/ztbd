from collections.abc import Callable
from typing import Any, Protocol


class BenchmarkAdapter(Protocol):
    def execute(self, operation: Any, params: Any | None = None) -> Any:
        ...

    def explain(self, operation: Any) -> str | None:
        ...

    def time_it(self, operation: Callable[[], Any]) -> tuple[Any, float]:
        ...

    def close(self) -> None:
        ...
