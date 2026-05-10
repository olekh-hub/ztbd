from typing import Any

import redis

from benchmarks.adapters.base import TimingMixin
from ztbd.config import RedisSettings


class RedisBenchmarkAdapter(TimingMixin):
    def __init__(self, settings: RedisSettings):
        self.client = redis.Redis(host=settings.host, port=settings.port, db=settings.db, decode_responses=True)

    def execute(self, operation: Any, params: Any | None = None) -> Any:
        if callable(operation):
            return operation(self.client)
        raise TypeError("Redis operations must be callables that accept a Redis client.")

    def explain(self, operation: Any) -> str | None:
        return None

    def close(self) -> None:
        self.client.close()
