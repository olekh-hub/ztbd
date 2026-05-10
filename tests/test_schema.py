from pathlib import Path

import pytest

from ztbd.repositories.mysql import mysql_load_statement
from ztbd.repositories.postgres import postgres_copy_statement
from ztbd.schema import DEFAULT_LOAD_PLAN, split_sql


def test_split_sql_ignores_empty_statements() -> None:
    assert list(split_sql("CREATE TABLE a(id int); ; SELECT 1;")) == ["CREATE TABLE a(id int)", "SELECT 1"]


def test_load_plan_validates_missing_files(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        DEFAULT_LOAD_PLAN.validate_files(tmp_path)


def test_mysql_load_statement_handles_special_tables() -> None:
    addresses = mysql_load_statement("addresses", Path("/tmp/addresses.csv"))
    orders = mysql_load_statement("orders", Path("/tmp/orders.csv"))

    assert "(customer_id, street, city, postcode)" in addresses
    assert "NULLIF(@coupon_id, '')" in orders


def test_postgres_copy_statement_uses_schema_columns() -> None:
    assert postgres_copy_statement("addresses") == (
        "COPY addresses (customer_id, street, city, postcode) "
        "FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL '')"
    )
