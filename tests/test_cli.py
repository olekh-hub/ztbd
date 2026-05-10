from ztbd.cli import parse_targets
from ztbd.config import DatabaseTarget


def test_parse_targets_expands_all() -> None:
    assert parse_targets(["all"]) == {
        DatabaseTarget.MYSQL,
        DatabaseTarget.POSTGRES,
        DatabaseTarget.MONGO,
        DatabaseTarget.REDIS,
    }


def test_parse_targets_expands_nosql() -> None:
    assert parse_targets(["nosql"]) == {DatabaseTarget.MONGO, DatabaseTarget.REDIS}
