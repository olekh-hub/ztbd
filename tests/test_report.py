import csv

from benchmarks.report import bootstrap_mean_ci, summarize_results, write_summary


def test_bootstrap_mean_ci_is_deterministic_for_seed() -> None:
    first = bootstrap_mean_ci([10.0, 20.0, 30.0], iterations=100, seed=7)
    second = bootstrap_mean_ci([10.0, 20.0, 30.0], iterations=100, seed=7)

    assert first == second
    assert first[0] <= 20.0 <= first[1]


def test_summarize_results_groups_by_test_key(tmp_path) -> None:
    input_path = tmp_path / "benchmark_results.csv"
    with input_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["scenario_id", "db", "size", "variant", "run_no", "status", "duration_ms", "rows_affected", "plan_hash", "error_type", "error_message"])
        writer.writerow(["r1", "mysql", "test", "idx", "1", "ok", "10.0", "1", "abc", "", ""])
        writer.writerow(["r1", "mysql", "test", "idx", "2", "failed", "", "", "", "RuntimeError", "boom"])
        writer.writerow(["r1", "mysql", "test", "idx", "3", "ok", "20.0", "1", "abc", "", ""])
        writer.writerow(["r1", "postgres", "test", "idx", "1", "ok", "30.0", "1", "def", "", ""])

    summaries = summarize_results(input_path, bootstrap_iterations=100, seed=1)

    assert len(summaries) == 2
    mysql = next(summary for summary in summaries if summary.key == ("r1", "mysql", "test", "idx"))
    assert mysql.as_row()["runs"] == "3"
    assert mysql.as_row()["failed_runs"] == "1"
    assert mysql.as_row()["mean_ms"] == "15.000"


def test_write_summary_creates_csv(tmp_path) -> None:
    input_path = tmp_path / "benchmark_results.csv"
    output_path = tmp_path / "summary.csv"
    input_path.write_text(
        "scenario_id,db,size,variant,run_no,status,duration_ms,rows_affected,plan_hash,error_type,error_message\n"
        "r1,mysql,test,idx,1,ok,10.0,1,abc,,\n",
        encoding="utf-8",
    )

    write_summary(output_path, summarize_results(input_path, bootstrap_iterations=10))

    text = output_path.read_text(encoding="utf-8")
    assert "bootstrap_mean_low_ms" in text
    assert "r1,mysql,test,idx,1,1,0,0,0.000,10.000" in text
