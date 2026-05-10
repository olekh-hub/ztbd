from typing import Any

import mysql.connector

from benchmarks.adapters.base import TimingMixin
from ztbd.config import MySqlSettings


class MySqlBenchmarkAdapter(TimingMixin):
    def __init__(self, settings: MySqlSettings):
        self.connection: Any = mysql.connector.connect(
            host=settings.host,
            port=settings.port,
            user=settings.user,
            password=settings.password,
            database=settings.database,
            allow_local_infile=True,
        )
        self.cursor: Any = self.connection.cursor(dictionary=True)

    def execute(self, operation: str, params: Any | None = None) -> dict[str, Any]:
        self.cursor.execute(operation, params)
        rows = self.cursor.fetchall() if self.cursor.with_rows else []
        self.connection.commit()
        rows_affected = self.cursor.rowcount if self.cursor.rowcount >= 0 else len(rows)
        return {"rows": rows, "rows_affected": rows_affected}

    def explain(self, operation: str) -> str | None:
        self.cursor.execute(f"EXPLAIN ANALYZE {operation}")
        return "\n".join(str(row) for row in self.cursor.fetchall())

    def close(self) -> None:
        self.cursor.close()
        self.connection.close()
