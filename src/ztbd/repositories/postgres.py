from pathlib import Path

from ztbd.schema import DEFAULT_LOAD_PLAN, POSTGRES_SCHEMA_PATH, TABLES, split_sql


def postgres_copy_statement(table: str) -> str:
    columns = ", ".join(DEFAULT_LOAD_PLAN.columns[table])
    return f"COPY {table} ({columns}) FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL '')"


class PostgresIngestRepository:
    def __init__(self, connection):
        self.connection = connection
        self.cursor = connection.cursor()

    def reset_schema(self) -> None:
        for table in reversed(TABLES):
            self.cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

        schema = POSTGRES_SCHEMA_PATH.read_text(encoding="utf-8")
        for statement in split_sql(schema):
            self.cursor.execute(statement)

    def load_table(self, table: str, csv_path: Path) -> None:
        with self.cursor.copy(postgres_copy_statement(table)) as copy:
            with csv_path.open("rb") as csv_file:
                while chunk := csv_file.read(1024 * 1024):
                    copy.write(chunk)

    def close(self) -> None:
        self.connection.commit()
        self.cursor.close()
        self.connection.close()
