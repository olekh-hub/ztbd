import argparse
import csv
import hashlib
from copy import copy
from pathlib import Path

from benchmarks.adapters.factory import create_benchmark_adapter
from benchmarks.config import DEFAULT_EXPLAIN_DIR, DEFAULT_RESULTS_DIR, RESULT_COLUMNS, BenchmarkRun
from benchmarks.scenarios.registry import get_scenarios, list_scenarios
from benchmarks.variants import VariantApplier
from ztbd.cli import add_ingest_args, build_settings
from ztbd.csv_store import CsvStore
from ztbd.ingestion import IngestionService
from ztbd.repositories.factory import create_mongo_repository, create_redis_repository, create_relational_repository
from ztbd.config import DatabaseTarget, IndexVariant


def parse_targets(raw_targets: list[str]) -> list[DatabaseTarget]:
    targets = set(raw_targets)
    if "all" in targets:
        return [DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO, DatabaseTarget.REDIS]
    if "nosql" in targets:
        targets.remove("nosql")
        targets.update({"mongo", "redis"})
    selected = {DatabaseTarget(target) for target in targets}
    return [target for target in [DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO, DatabaseTarget.REDIS] if target in selected]


def parse_variants(raw_variant: str) -> list[IndexVariant]:
    if raw_variant == "both":
        return [IndexVariant.NO_IDX, IndexVariant.IDX]
    return [IndexVariant(raw_variant)]


def parse_sizes(raw_size: str) -> list[str]:
    if raw_size == "all":
        return ["s", "m", "l"]
    return [raw_size]


def args_for_size(args: argparse.Namespace, size: str) -> argparse.Namespace:
    sized_args = copy(args)
    if args.size == "all":
        sized_args.data_dir = args.data_dir / size
    return sized_args


def plan_hash(plan: str | None) -> str:
    if not plan:
        return ""
    return hashlib.sha256(plan.encode("utf-8")).hexdigest()[:12]


def result_path(results_dir: Path, size: str | None = None) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    if size is None:
        return results_dir / "benchmark_results.csv"
    return results_dir / f"benchmark_results_{size}.csv"


def concat_size_results(results_dir: Path, sizes: list[str]) -> Path:
    combined = result_path(results_dir)
    with combined.open("w", newline="", encoding="utf-8") as out_file:
        writer = csv.DictWriter(out_file, fieldnames=RESULT_COLUMNS)
        writer.writeheader()
        for size in sizes:
            per_size = result_path(results_dir, size)
            if not per_size.exists():
                continue
            with per_size.open(newline="", encoding="utf-8") as in_file:
                reader = csv.DictReader(in_file)
                for row in reader:
                    writer.writerow(row)
    return combined


def sanitize_error(message: str, limit: int = 240) -> str:
    return " ".join(message.split())[:limit]


def load_completed_runs(path: Path) -> set[tuple[str, str, str, str, int]]:
    if not path.exists():
        return set()
    completed: set[tuple[str, str, str, str, int]] = set()
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row.get("status") not in {"ok", "skipped"}:
                continue
            try:
                run_no = int(row["run_no"])
            except (KeyError, ValueError):
                continue
            completed.add((row["scenario_id"], row["db"], row["size"], row["variant"], run_no))
    return completed


def write_result(
    path: Path,
    run: BenchmarkRun,
    duration_ms: float | None,
    rows_affected: int | None,
    plan: str | None,
    status: str = "ok",
    error_type: str = "",
    error_message: str = "",
) -> None:
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=RESULT_COLUMNS)
        if not exists:
            writer.writeheader()
        writer.writerow(
            {
                "scenario_id": run.scenario_id,
                "db": run.target.value,
                "size": run.size,
                "variant": run.variant.value,
                "run_no": run.run_no,
                "status": status,
                "duration_ms": f"{duration_ms:.3f}" if duration_ms is not None else "",
                "rows_affected": rows_affected if rows_affected is not None else "",
                "plan_hash": plan_hash(plan),
                "error_type": error_type,
                "error_message": sanitize_error(error_message),
            }
        )


def write_explain(explain_dir: Path, run: BenchmarkRun, plan: str | None) -> None:
    if not plan:
        return
    explain_dir.mkdir(parents=True, exist_ok=True)
    path = explain_dir / f"{run.scenario_id}_{run.target.value}_{run.size}_{run.variant.value}.txt"
    path.write_text(plan, encoding="utf-8")


def run_benchmark(args: argparse.Namespace) -> None:
    scenarios = get_scenarios(args.scenario)
    targets = parse_targets(args.db)
    variants = parse_variants(args.variant)
    sizes = parse_sizes(args.size)
    applier = VariantApplier()

    for size in sizes:
        sized_args = args_for_size(args, size)
        settings = build_settings(sized_args)
        result_file = result_path(args.results_dir, size)
        completed = load_completed_runs(result_file) if args.resume else set()
        if args.resume and completed:
            print(f"Resume: {len(completed)} completed runs found in {result_file}")
        frames_cache: dict[str, object] = {}
        for target in targets:
            target_has_pending = any(
                (scenario.scenario_id, target.value, size, variant.value, run_no) not in completed
                for variant in variants
                for scenario in scenarios
                for run_no in range(1, args.runs + 1)
            )
            if not target_has_pending:
                print(f"Resume: all runs for {target.value} size={size} already complete, skipping")
                continue
            if args.reset_before_size:
                reset_target(settings, target, frames_cache)
            adapter = create_benchmark_adapter(target, settings)
            try:
                for variant in variants:
                    applier.apply(adapter, target, variant)
                    for scenario in scenarios:
                        if not scenario.supports(target):
                            for run_no in range(1, args.runs + 1):
                                key = (scenario.scenario_id, target.value, size, variant.value, run_no)
                                if key in completed:
                                    continue
                                run = BenchmarkRun(scenario.scenario_id, target, size, variant, run_no)
                                write_result(
                                    result_file,
                                    run,
                                    duration_ms=None,
                                    rows_affected=None,
                                    plan=None,
                                    status="skipped",
                                    error_type="UnsupportedScenario",
                                    error_message=f"{scenario.scenario_id} is not supported for {target.value}",
                                )
                            continue
                        operation = scenario.operation_for(target)
                        for run_no in range(1, args.runs + 1):
                            key = (scenario.scenario_id, target.value, size, variant.value, run_no)
                            if key in completed:
                                continue
                            if args.reset_before_run and scenario.mutating:
                                adapter.close()
                                reset_target(settings, target, frames_cache)
                                adapter = create_benchmark_adapter(target, settings)
                                if variant != IndexVariant.NO_IDX:
                                    applier.apply(adapter, target, variant)
                            run = BenchmarkRun(scenario.scenario_id, target, size, variant, run_no)
                            try:
                                result, duration_ms = adapter.time_it(lambda: operation(adapter))
                                rows_affected = int(result.get("rows_affected", 0)) if isinstance(result, dict) else 0
                                explain = scenario.explain_for(target)
                                plan = explain(adapter) if explain is not None else None
                                write_result(result_file, run, duration_ms, rows_affected, plan)
                                write_explain(args.explain_dir, run, plan)
                                print(
                                    f"{run.scenario_id} {target.value} {size} {variant.value} "
                                    f"run {run_no}: {duration_ms:.3f} ms"
                                )
                            except Exception as error:
                                write_result(
                                    result_file,
                                    run,
                                    duration_ms=None,
                                    rows_affected=None,
                                    plan=None,
                                    status="failed",
                                    error_type=type(error).__name__,
                                    error_message=str(error),
                                )
                                print(
                                    f"{run.scenario_id} {target.value} {size} {variant.value} "
                                    f"run {run_no}: failed ({type(error).__name__})"
                                )
            finally:
                adapter.close()

    if len(sizes) > 1:
        concat_size_results(args.results_dir, sizes)


def reset_target(settings, target: DatabaseTarget, frames_cache: dict | None = None) -> None:
    relational = {}
    document_repository = None
    key_value_repository = None

    if target in {DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES}:
        relational[target] = create_relational_repository(target, settings)
    elif target == DatabaseTarget.MONGO:
        document_repository = create_mongo_repository(settings)
    elif target == DatabaseTarget.REDIS:
        key_value_repository = create_redis_repository(settings)

    IngestionService(
        settings=settings,
        store=CsvStore(settings.data_dir),
        relational_repositories=relational,
        document_repository=document_repository,
        key_value_repository=key_value_repository,
        static_frames=frames_cache,
    ).run({target})

    if key_value_repository is not None:
        key_value_repository.close()
    if document_repository is not None and hasattr(document_repository, "close"):
        document_repository.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run ZTBD benchmark scenarios.")
    parser.add_argument("--scenario", default="all", help="Scenario id to run, or all.")
    parser.add_argument(
        "--db",
        nargs="+",
        default=["all"],
        choices=["all", "mysql", "postgres", "mongo", "redis", "nosql"],
    )
    parser.add_argument("--size", default="test", choices=["test", "s", "m", "l", "all"])
    parser.add_argument("--variant", default="both", choices=["no_idx", "idx", "both"])
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--results-dir", type=Path, default=DEFAULT_RESULTS_DIR)
    parser.add_argument("--explain-dir", type=Path, default=DEFAULT_EXPLAIN_DIR)
    parser.add_argument("--reset-before-run", action="store_true", help="Reingest the selected dataset before each mutating run.")
    parser.add_argument("--reset-before-size", action="store_true", help="Reingest each size dataset before running that size for each database.")
    parser.add_argument("--resume", action="store_true", help="Skip (scenario,db,size,variant,run_no) entries already present with status ok/skipped in the per-size CSVs under --results-dir; failed/missing runs are retried.")
    parser.add_argument("--list-scenarios", action="store_true")
    add_ingest_args(parser)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.list_scenarios:
        for scenario in list_scenarios():
            targets = ", ".join(target.value for target in sorted(scenario.supported_targets, key=lambda item: item.value))
            print(f"{scenario.scenario_id}: {scenario.name} [{targets}]")
        return
    run_benchmark(args)


if __name__ == "__main__":
    main()
