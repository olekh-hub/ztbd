#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RUN_ID="${RUN_ID:-$(date +"%Y%m%d_%H%M%S")}"
REPORT_ROOT="${REPORT_ROOT:-reports/runs}"
RUN_DIR="${RUN_DIR:-$REPORT_ROOT/$RUN_ID}"
DATA_DIR="${DATA_DIR:-data}"
SCENARIO="${SCENARIO:-all}"
DB="${DB:-all}"
SIZE="${SIZE:-all}"
VARIANT="${VARIANT:-both}"
RUNS="${RUNS:-3}"
BOOTSTRAP_ITERATIONS="${BOOTSTRAP_ITERATIONS:-2000}"
CONFIDENCE="${CONFIDENCE:-0.95}"
SEED="${SEED:-42}"
read -r -a DB_ARGS <<< "$DB"

RESULTS_DIR="$RUN_DIR"
RESULTS_FILE="$RESULTS_DIR/benchmark_results.csv"
SUMMARY_FILE="$RUN_DIR/benchmark_summary.csv"
FIGURES_DIR="$RUN_DIR/figures"
EXPLAIN_DIR="$RUN_DIR/explain_plans"

log() {
  printf '[%s] %s\n' "$(date +"%H:%M:%S")" "$*"
}

wait_for() {
  local name="$1"
  shift
  local attempts="${WAIT_ATTEMPTS:-60}"
  local delay="${WAIT_DELAY:-2}"

  for ((attempt = 1; attempt <= attempts; attempt++)); do
    if "$@" >/dev/null 2>&1; then
      log "$name is ready"
      return 0
    fi
    sleep "$delay"
  done

  log "$name did not become ready in time"
  return 1
}

data_target_for_size() {
  local size="$1"
  if [[ "$SIZE" == "all" ]]; then
    printf '%s/%s' "$DATA_DIR" "$size"
  else
    printf '%s' "$DATA_DIR"
  fi
}

generate_if_missing() {
  local size="$1"
  local target_dir
  target_dir="$(data_target_for_size "$size")"

  if [[ -f "$target_dir/customers.csv" && -f "$target_dir/orders.csv" && -f "$target_dir/order_items.csv" ]]; then
    log "Data for size '$size' already exists in $target_dir"
    return 0
  fi

  log "Generating size '$size' data in $target_dir"
  uv run ztbd generate --size "$size" --out-dir "$target_dir" --seed "$SEED"
}

sizes_to_generate() {
  if [[ "$SIZE" == "all" ]]; then
    printf '%s\n' s m l
  else
    printf '%s\n' "$SIZE"
  fi
}

mkdir -p "$RUN_DIR" "$FIGURES_DIR" "$EXPLAIN_DIR"

log "Starting Docker containers"
docker compose up -d

log "Waiting for database services"
wait_for "PostgreSQL" docker compose exec -T postgres pg_isready -U admin -d ecommerce_db
wait_for "MySQL" docker compose exec -T mysql mysqladmin ping -uroot -ppassword
wait_for "MongoDB" docker compose exec -T mongodb mongosh --quiet --eval "db.adminCommand('ping').ok"
wait_for "Redis" docker compose exec -T redis redis-cli ping

while IFS= read -r size; do
  generate_if_missing "$size"
done < <(sizes_to_generate)

log "Running benchmarks into $RESULTS_FILE"
uv run ztbd-benchmark \
  --scenario "$SCENARIO" \
  --db "${DB_ARGS[@]}" \
  --size "$SIZE" \
  --variant "$VARIANT" \
  --runs "$RUNS" \
  --data-dir "$DATA_DIR" \
  --results-dir "$RESULTS_DIR" \
  --explain-dir "$EXPLAIN_DIR" \
  --reset-before-size \
  --reset-before-run

log "Generating summary report"
uv run ztbd-report \
  --input "$RESULTS_FILE" \
  --output "$SUMMARY_FILE" \
  --bootstrap-iterations "$BOOTSTRAP_ITERATIONS" \
  --confidence "$CONFIDENCE" \
  --seed "$SEED"

log "Generating plots"
uv run ztbd-plots \
  --results "$RESULTS_FILE" \
  --summary "$SUMMARY_FILE" \
  --out-dir "$FIGURES_DIR"

log "Report run complete: $RUN_DIR"
