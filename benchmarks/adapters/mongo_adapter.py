from pathlib import Path
from typing import Any

from pymongo import MongoClient

from benchmarks.adapters.base import TimingMixin
from ztbd.config import MongoSettings


class MongoBenchmarkAdapter(TimingMixin):
    def __init__(self, settings: MongoSettings):
        self.client = MongoClient(settings.uri)
        self.database = self.client[settings.database]

    def execute(self, operation: Any, params: Any | None = None) -> Any:
        if callable(operation):
            return operation(self.database)
        raise TypeError("Mongo operations must be callables that accept a database.")

    def execute_script(self, path: Path, ignore_errors: bool = False) -> None:
        for line in path.read_text(encoding="utf-8").splitlines():
            statement = line.strip().rstrip(";")
            if not statement or statement.startswith("//"):
                continue
            try:
                self._execute_index_statement(statement)
            except Exception:
                if not ignore_errors:
                    raise

    def explain(self, operation: Any) -> str | None:
        if callable(operation):
            return str(operation(self.database, explain=True))
        return None

    def close(self) -> None:
        self.client.close()

    def _execute_index_statement(self, statement: str) -> None:
        # Supports the generated db.<collection>.createIndex/dropIndex files.
        prefix = "db."
        if not statement.startswith(prefix):
            raise ValueError(f"Unsupported Mongo script statement: {statement}")
        collection_name, call = statement[len(prefix) :].split(".", 1)
        collection = self.database[collection_name]
        if call.startswith("createIndex("):
            expression = call.removeprefix("createIndex(").removesuffix(")")
            keys_text, options_text = expression.split("},", 1)
            keys = self._parse_mongo_object(keys_text + "}")
            options = self._parse_mongo_object(options_text.strip())
            collection.create_index(list(keys.items()), **options)
            return
        if call.startswith("dropIndex("):
            index_name = call.removeprefix("dropIndex(").removesuffix(")").strip("\"'")
            collection.drop_index(index_name)
            return
        raise ValueError(f"Unsupported Mongo script call: {call}")

    def _parse_mongo_object(self, value: str) -> dict:
        import json
        import re

        normalized = re.sub(r"([,{]\s*)([A-Za-z_][A-Za-z0-9_.]*)\s*:", r'\1"\2":', value)
        normalized = normalized.replace("'", '"')
        return json.loads(normalized)
