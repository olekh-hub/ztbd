from dataclasses import dataclass
from pathlib import Path

from ztbd.config import PROJECT_ROOT, DatabaseTarget, IndexVariant


RESULT_COLUMNS = [
    "scenario_id",
    "db",
    "size",
    "variant",
    "run_no",
    "status",
    "duration_ms",
    "rows_affected",
    "plan_hash",
    "error_type",
    "error_message",
]


@dataclass(frozen=True)
class BenchmarkRun:
    scenario_id: str
    target: DatabaseTarget
    size: str
    variant: IndexVariant
    run_no: int


DEFAULT_RESULTS_DIR = PROJECT_ROOT / "benchmarks" / "results"
DEFAULT_EXPLAIN_DIR = PROJECT_ROOT / "explain_plans"
DEFAULT_REPORTS_DIR = PROJECT_ROOT / "reports"
