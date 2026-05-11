import csv
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd

from ztbd.schema import DEFAULT_LOAD_PLAN


class CsvStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def path_for(self, table: str) -> Path:
        return self.data_dir / f"{table}.csv"

    def ensure_dir(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def validate(self) -> None:
        DEFAULT_LOAD_PLAN.validate_files(self.data_dir)

    def write_rows(self, table: str, rows: Iterable[Sequence[object]]) -> None:
        self.ensure_dir()
        with self.path_for(table).open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(DEFAULT_LOAD_PLAN.columns[table])
            writer.writerows(rows)

    def read_frame(self, table: str, **kwargs) -> pd.DataFrame:
        return pd.read_csv(self.path_for(table), **kwargs)
