from pathlib import Path

from benchmarks.config import BenchmarkRun
from benchmarks.runner import (
    concat_size_results,
    parse_sizes,
    parse_targets,
    parse_variants,
    plan_hash,
    result_path,
    write_result,
)
from benchmarks.variants import INDEX_FILES
from ztbd.config import DatabaseTarget, IndexVariant


def test_parse_benchmark_targets_and_variants() -> None:
    assert parse_targets(["nosql"]) == [DatabaseTarget.MONGO, DatabaseTarget.REDIS]
    assert parse_variants("both") == [IndexVariant.NO_IDX, IndexVariant.IDX]
    assert parse_sizes("all") == ["s", "m", "l"]


def test_index_files_exist() -> None:
    for path in INDEX_FILES.values():
        assert path.exists()


def test_read_scenarios_are_registered() -> None:
    from benchmarks.scenarios.registry import SCENARIOS

    for scenario_id in [
        "r1",
        "r2",
        "r3",
        "r4",
        "r5",
        "r6",
        "c1",
        "c2",
        "c3",
        "c4",
        "c5",
        "c6",
        "u1",
        "u2",
        "u3",
        "u4",
        "u5",
        "u6",
        "d1",
        "d2",
        "d3",
        "d4",
        "d5",
        "d6",
    ]:
        assert scenario_id in SCENARIOS


def test_mutating_scenarios_are_marked() -> None:
    from benchmarks.scenarios.registry import SCENARIOS

    assert SCENARIOS["c1"].mutating is True
    assert SCENARIOS["u1"].mutating is True
    assert SCENARIOS["d1"].mutating is True


def test_write_result_creates_csv(tmp_path: Path) -> None:
    output = tmp_path / "results.csv"
    run = BenchmarkRun("smoke", DatabaseTarget.MYSQL, "test", IndexVariant.NO_IDX, 1)

    write_result(output, run, 12.3456, 1, "plan")

    text = output.read_text(encoding="utf-8")
    assert "scenario_id,db,size,variant,run_no,status,duration_ms,rows_affected,plan_hash,error_type,error_message" in text
    assert "smoke,mysql,test,no_idx,1,ok,12.346,1," in text
    assert plan_hash("plan")


def test_result_path_uses_per_size_filename(tmp_path: Path) -> None:
    assert result_path(tmp_path, "s").name == "benchmark_results_s.csv"
    assert result_path(tmp_path, "m").name == "benchmark_results_m.csv"
    assert result_path(tmp_path).name == "benchmark_results.csv"


def test_concat_size_results_merges_per_size_files(tmp_path: Path) -> None:
    for size in ["s", "m"]:
        run = BenchmarkRun("smoke", DatabaseTarget.MYSQL, size, IndexVariant.NO_IDX, 1)
        write_result(result_path(tmp_path, size), run, 1.0, 1, None)

    combined = concat_size_results(tmp_path, ["s", "m", "l"])

    text = combined.read_text(encoding="utf-8")
    assert text.count("smoke,mysql,s,no_idx") == 1
    assert text.count("smoke,mysql,m,no_idx") == 1
    assert "scenario_id,db,size,variant" in text.splitlines()[0]
