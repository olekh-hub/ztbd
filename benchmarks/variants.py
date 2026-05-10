from pathlib import Path

from ztbd.config import DatabaseTarget, IndexVariant, PROJECT_ROOT
from ztbd.schema import split_sql


SCHEMA_DIR = PROJECT_ROOT / "schemas"

INDEX_FILES = {
    (DatabaseTarget.MYSQL, IndexVariant.IDX): SCHEMA_DIR / "indexes_mysql.sql",
    (DatabaseTarget.MYSQL, IndexVariant.NO_IDX): SCHEMA_DIR / "indexes_drop_mysql.sql",
    (DatabaseTarget.POSTGRES, IndexVariant.IDX): SCHEMA_DIR / "indexes_postgres.sql",
    (DatabaseTarget.POSTGRES, IndexVariant.NO_IDX): SCHEMA_DIR / "indexes_drop_postgres.sql",
    (DatabaseTarget.MONGO, IndexVariant.IDX): SCHEMA_DIR / "indexes_mongo.js",
    (DatabaseTarget.MONGO, IndexVariant.NO_IDX): SCHEMA_DIR / "indexes_drop_mongo.js",
}


class VariantApplier:
    def __init__(self, ignore_drop_errors: bool = True):
        self.ignore_drop_errors = ignore_drop_errors

    def apply(self, adapter, target: DatabaseTarget, variant: IndexVariant) -> None:
        if target == DatabaseTarget.REDIS:
            return

        path = INDEX_FILES[(target, variant)]
        if target in {DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES}:
            self._apply_sql(adapter, path, variant)
            return

        if target == DatabaseTarget.MONGO:
            adapter.execute_script(path, ignore_errors=variant == IndexVariant.NO_IDX)

    def _apply_sql(self, adapter, path: Path, variant: IndexVariant) -> None:
        for statement in split_sql(path.read_text(encoding="utf-8")):
            try:
                adapter.execute(statement)
            except Exception as error:
                if self._can_ignore_sql_error(error, variant):
                    continue
                raise

    def _can_ignore_sql_error(self, error: Exception, variant: IndexVariant) -> bool:
        message = str(error).lower()
        if variant == IndexVariant.NO_IDX and self.ignore_drop_errors:
            return True
        if variant == IndexVariant.IDX:
            duplicate_markers = ["duplicate key name", "relation", "already exists"]
            return any(marker in message for marker in duplicate_markers)
        return False
