from datetime import date


BATCH = 25
MUTATION_BASE_ID = 9_000_000


def sql_scalar(adapter, query: str, default: int = 0) -> int:
    result = adapter.execute(query)
    rows = result.get("rows", [])
    if not rows:
        return default
    value = next(iter(rows[0].values()))
    return int(value or default)


def sql_many(adapter, query: str, rows: list[tuple]) -> dict:
    adapter.cursor.executemany(query, rows)
    adapter.connection.commit()
    return {"rows": [], "rows_affected": adapter.cursor.rowcount if adapter.cursor.rowcount >= 0 else len(rows)}


def sql_one(adapter, query: str):
    rows = adapter.execute(query).get("rows", [])
    return rows[0] if rows else None


def today_iso() -> str:
    return date.today().isoformat()
