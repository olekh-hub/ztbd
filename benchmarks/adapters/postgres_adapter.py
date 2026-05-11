from typing import Any, cast

import psycopg
from psycopg.rows import dict_row

from benchmarks.adapters.base import TimingMixin
from ztbd.config import PostgresSettings


class PostgresBenchmarkAdapter(TimingMixin):
    def __init__(self, settings: PostgresSettings):
        self.connection: Any = psycopg.connect(
            host=settings.host,
            port=settings.port,
            user=settings.user,
            password=settings.password,
            dbname=settings.database,
            row_factory=cast(Any, dict_row),
        )
        self.cursor: Any = self.connection.cursor()

    def execute(self, operation: str, params: Any | None = None) -> dict[str, Any]:
        self.cursor.execute(operation, params)
        rows = self.cursor.fetchall() if self.cursor.description else []
        self.connection.commit()
        rows_affected = self.cursor.rowcount if self.cursor.rowcount >= 0 else len(rows)
        return {"rows": rows, "rows_affected": rows_affected}

    def explain(self, operation: str) -> str | None:
        self.cursor.execute(f"EXPLAIN (ANALYZE, BUFFERS) {operation}")
        return "\n".join(str(row) for row in self.cursor.fetchall())

    def close(self) -> None:
        self.cursor.close()
        self.connection.close()
