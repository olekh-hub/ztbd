import csv

from benchmarks.plots import generate_plots
from benchmarks.report import summarize_results, write_summary


def write_sample_results(path) -> None:
    rows = [
        ["r1", "mysql", "s", "no_idx", "1", "ok", "20.0", "1", "a", "", ""],
        ["r1", "mysql", "s", "idx", "1", "ok", "10.0", "1", "b", "", ""],
        ["r1", "postgres", "s", "no_idx", "1", "failed", "", "", "", "RuntimeError", "boom"],
        ["r1", "postgres", "s", "idx", "1", "ok", "12.0", "1", "c", "", ""],
        ["c1", "mysql", "s", "no_idx", "1", "ok", "30.0", "25", "", "", ""],
        ["c1", "mysql", "s", "idx", "1", "ok", "40.0", "25", "", "", ""],
        ["u1", "mysql", "m", "idx", "1", "ok", "50.0", "1", "", "", ""],
        ["d1", "mysql", "l", "idx", "1", "skipped", "", "", "", "UnsupportedScenario", "skip"],
    ]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["scenario_id", "db", "size", "variant", "run_no", "status", "duration_ms", "rows_affected", "plan_hash", "error_type", "error_message"])
        writer.writerows(rows)


def test_generate_plots_creates_figures(tmp_path) -> None:
    results = tmp_path / "benchmark_results.csv"
    summary = tmp_path / "benchmark_summary.csv"
    out_dir = tmp_path / "figures"
    write_sample_results(results)
    write_summary(summary, summarize_results(results, bootstrap_iterations=20))

    paths = generate_plots(results, summary, out_dir)

    assert len(paths) == 14
    for path in paths:
        assert path.exists()
        assert path.stat().st_size > 0
