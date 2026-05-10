import argparse
import csv
import random
import statistics
from dataclasses import dataclass
from pathlib import Path

from benchmarks.config import DEFAULT_REPORTS_DIR, DEFAULT_RESULTS_DIR


GROUP_COLUMNS = ["scenario_id", "db", "size", "variant"]
SUMMARY_COLUMNS = [
    *GROUP_COLUMNS,
    "runs",
    "ok_runs",
    "failed_runs",
    "skipped_runs",
    "failure_rate",
    "mean_ms",
    "stdev_ms",
    "min_ms",
    "p50_ms",
    "p95_ms",
    "max_ms",
    "bootstrap_mean_low_ms",
    "bootstrap_mean_high_ms",
]


@dataclass(frozen=True)
class ResultGroup:
    values: list[float]
    statuses: list[str]


@dataclass(frozen=True)
class DistributionSummary:
    key: tuple[str, str, str, str]
    values: list[float]
    statuses: list[str]
    bootstrap_low: float
    bootstrap_high: float

    def as_row(self) -> dict[str, str]:
        scenario_id, db, size, variant = self.key
        total = len(self.statuses)
        ok_runs = self.statuses.count("ok")
        failed_runs = self.statuses.count("failed")
        skipped_runs = self.statuses.count("skipped")
        return {
            "scenario_id": scenario_id,
            "db": db,
            "size": size,
            "variant": variant,
            "runs": str(total),
            "ok_runs": str(ok_runs),
            "failed_runs": str(failed_runs),
            "skipped_runs": str(skipped_runs),
            "failure_rate": format_float(failed_runs / total if total else 0.0),
            "mean_ms": format_optional(statistics.fmean(self.values) if self.values else None),
            "stdev_ms": format_optional(statistics.stdev(self.values) if len(self.values) > 1 else (0.0 if self.values else None)),
            "min_ms": format_optional(min(self.values) if self.values else None),
            "p50_ms": format_optional(percentile(self.values, 50) if self.values else None),
            "p95_ms": format_optional(percentile(self.values, 95) if self.values else None),
            "max_ms": format_optional(max(self.values) if self.values else None),
            "bootstrap_mean_low_ms": format_optional(self.bootstrap_low if self.values else None),
            "bootstrap_mean_high_ms": format_optional(self.bootstrap_high if self.values else None),
        }


def format_float(value: float) -> str:
    return f"{value:.3f}"


def format_optional(value: float | None) -> str:
    return "" if value is None else format_float(value)


def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * pct / 100
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def bootstrap_mean_ci(
    values: list[float],
    iterations: int = 2_000,
    confidence: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return values[0], values[0]

    rng = random.Random(seed)
    means = []
    for _ in range(iterations):
        sample = [rng.choice(values) for _ in values]
        means.append(statistics.fmean(sample))

    alpha = (1 - confidence) / 2
    return percentile(means, alpha * 100), percentile(means, (1 - alpha) * 100)


def load_result_groups(path: Path) -> dict[tuple[str, str, str, str], ResultGroup]:
    groups: dict[tuple[str, str, str, str], ResultGroup] = {}
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            key = (row["scenario_id"], row["db"], row["size"], row["variant"])
            group = groups.setdefault(key, ResultGroup(values=[], statuses=[]))
            status = row.get("status") or "ok"
            group.statuses.append(status)
            if status == "ok" and row.get("duration_ms"):
                group.values.append(float(row["duration_ms"]))
    return groups


def summarize_results(
    input_path: Path,
    bootstrap_iterations: int = 2_000,
    confidence: float = 0.95,
    seed: int = 42,
) -> list[DistributionSummary]:
    groups = load_result_groups(input_path)
    summaries = []
    for key, group in sorted(groups.items()):
        values = group.values
        statuses = group.statuses
        low, high = bootstrap_mean_ci(values, iterations=bootstrap_iterations, confidence=confidence, seed=seed)
        summaries.append(DistributionSummary(key=key, values=values, statuses=statuses, bootstrap_low=low, bootstrap_high=high))
    return summaries


def write_summary(path: Path, summaries: list[DistributionSummary]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=SUMMARY_COLUMNS)
        writer.writeheader()
        for summary in summaries:
            writer.writerow(summary.as_row())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize benchmark result distributions with bootstrap confidence intervals.")
    parser.add_argument("--input", type=Path, default=DEFAULT_RESULTS_DIR / "benchmark_results.csv")
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORTS_DIR / "benchmark_summary.csv")
    parser.add_argument("--bootstrap-iterations", type=int, default=2_000)
    parser.add_argument("--confidence", type=float, default=0.95)
    parser.add_argument("--seed", type=int, default=42)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summaries = summarize_results(
        args.input,
        bootstrap_iterations=args.bootstrap_iterations,
        confidence=args.confidence,
        seed=args.seed,
    )
    write_summary(args.output, summaries)
    print(f"Wrote {len(summaries)} benchmark summaries to {args.output}")


if __name__ == "__main__":
    main()
