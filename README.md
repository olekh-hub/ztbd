# ztbd

Python tooling for generating ecommerce CSV data and ingesting it into MySQL, PostgreSQL, MongoDB, and Redis.

## Setup

```sh
uv sync
docker compose up -d
```

## Generate Data

Generate deterministic CSV data with a named size profile:

```sh
uv run ztbd generate --size test --out-dir data/test
uv run ztbd generate --size s --out-dir data/s
uv run ztbd generate --size m --out-dir data/m
uv run ztbd generate --size l --out-dir data/l
```

Available sizes are `test`, `s`, `m`, and `l`.

## Ingest Data

Ingest into all configured databases:

```sh
uv run ztbd ingest --data-dir data/test
```

Ingest selected targets:

```sh
uv run ztbd ingest --targets mysql postgres --data-dir data/test
uv run ztbd ingest --targets nosql --data-dir data/test
```

Connection defaults match `docker-compose.yml`; override them with the `ztbd ingest --help` options.

## Tests

```sh
uv run pytest
```

Integration tests that require running databases should be marked with `integration` and kept out of the default fast test path.

## Benchmarks

Index definitions live in `schemas/`:

- `indexes_mysql.sql` / `indexes_drop_mysql.sql`
- `indexes_postgres.sql` / `indexes_drop_postgres.sql`
- `indexes_mongo.js` / `indexes_drop_mongo.js`
- `indexes_redis.md`

List registered benchmark scenarios:

```sh
uv run ztbd-benchmark --list-scenarios
```

Run the current smoke benchmark against selected databases:

```sh
uv run ztbd-benchmark --scenario smoke --db mysql postgres --size test --variant both --runs 3
```

Run the implemented READ scenarios:

```sh
uv run ztbd-benchmark --scenario r1 --db all --size test --variant both --runs 3
uv run ztbd-benchmark --scenario r2 --db mysql postgres mongo --size test --variant both --runs 3
```

Run mutating scenarios with dataset reset before each run:

```sh
uv run ztbd-benchmark --scenario c1 --db all --size test --variant both --runs 3 --reset-before-run
uv run ztbd-benchmark --scenario u1 --db all --size test --variant both --runs 3 --reset-before-run
uv run ztbd-benchmark --scenario d1 --db all --size test --variant both --runs 3 --reset-before-run
```

Run the full benchmark matrix after generating `data/s`, `data/m`, and `data/l`:

```sh
uv run ztbd-benchmark --scenario all --db all --size all --variant both --runs 3 --data-dir data --reset-before-size --reset-before-run
```

Or generate all datasets and run the full matrix with:

```sh
bash benchmarks/run_full_matrix.sh
```

The script starts Docker containers, waits for all database services, generates missing data, runs the benchmark matrix with data resets, writes a timestamped run under `reports/runs/<timestamp>/`, then generates the summary CSV and plots. You can override defaults with environment variables:

```sh
RUN_ID=my_experiment RUNS=5 SIZE=test DB="mysql postgres" bash benchmarks/run_full_matrix.sh
```

Manual benchmark runs append to `benchmarks/results/benchmark_results.csv` unless `--results-dir` is provided. READ scenario explain plans are written to `explain_plans/` unless `--explain-dir` is provided.

Summarize per-test distributions with bootstrap confidence intervals:

```sh
uv run ztbd-report \
  --input benchmarks/results/benchmark_results.csv \
  --output reports/benchmark_summary.csv
```

The report groups results by `scenario_id`, `db`, `size`, and `variant`, then writes mean, standard deviation, min/max, p50, p95, and bootstrap mean confidence intervals.

Generate plots from the raw and summarized benchmark outputs:

```sh
uv run ztbd-plots \
  --results benchmarks/results/benchmark_results.csv \
  --summary reports/benchmark_summary.csv \
  --out-dir reports/figures
```

The plot set includes a failure heatmap, IDX-vs-NO_IDX speedup, H1 suite comparison, scaling chart, duration distribution, engine leaderboard, and rows-affected sanity chart. Failed and skipped runs are preserved in the raw CSV and summarized before plotting.
