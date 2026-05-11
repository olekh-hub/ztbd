from benchmarks.adapters.mongo_adapter import MongoBenchmarkAdapter
from benchmarks.adapters.mysql_adapter import MySqlBenchmarkAdapter
from benchmarks.adapters.postgres_adapter import PostgresBenchmarkAdapter
from benchmarks.adapters.redis_adapter import RedisBenchmarkAdapter
from ztbd.config import AppSettings, DatabaseTarget


def create_benchmark_adapter(target: DatabaseTarget, settings: AppSettings):
    if target == DatabaseTarget.MYSQL:
        return MySqlBenchmarkAdapter(settings.mysql)
    if target == DatabaseTarget.POSTGRES:
        return PostgresBenchmarkAdapter(settings.postgres)
    if target == DatabaseTarget.MONGO:
        return MongoBenchmarkAdapter(settings.mongo)
    if target == DatabaseTarget.REDIS:
        return RedisBenchmarkAdapter(settings.redis)
    raise ValueError(f"Unsupported benchmark target: {target}")
