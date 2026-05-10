from benchmarks.scenarios.base import ScenarioDefinition
from benchmarks.scenarios.create import CREATE_SCENARIOS
from benchmarks.scenarios.delete import DELETE_SCENARIOS
from benchmarks.scenarios.read import READ_SCENARIOS
from benchmarks.scenarios.update import UPDATE_SCENARIOS
from ztbd.config import DatabaseTarget


def sql_smoke(adapter) -> dict:
    return adapter.execute("SELECT 1 AS ok")


def mongo_smoke(adapter) -> dict:
    result = adapter.execute(lambda db: db.command("ping"))
    return {"rows": [result], "rows_affected": 0}


def redis_smoke(adapter) -> dict:
    result = adapter.execute(lambda client: client.ping())
    return {"rows": [{"ok": result}], "rows_affected": 0}


SCENARIOS = {
    "smoke": ScenarioDefinition(
        scenario_id="smoke",
        name="Adapter connectivity smoke test",
        supported_targets={DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO, DatabaseTarget.REDIS},
        operation_by_target={
            DatabaseTarget.MYSQL: sql_smoke,
            DatabaseTarget.POSTGRES: sql_smoke,
            DatabaseTarget.MONGO: mongo_smoke,
            DatabaseTarget.REDIS: redis_smoke,
        },
    ),
    **READ_SCENARIOS,
    **CREATE_SCENARIOS,
    **UPDATE_SCENARIOS,
    **DELETE_SCENARIOS,
}


def list_scenarios() -> list[ScenarioDefinition]:
    return list(SCENARIOS.values())


def get_scenarios(selection: str) -> list[ScenarioDefinition]:
    if selection == "all":
        return list_scenarios()
    if selection not in SCENARIOS:
        raise KeyError(f"Unknown scenario '{selection}'. Implement it in benchmarks/scenarios/registry.py.")
    return [SCENARIOS[selection]]
