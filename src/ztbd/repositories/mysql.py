import csv
from pathlib import Path

import mysql.connector

from ztbd.schema import MYSQL_SCHEMA_PATH, TABLES, split_sql


def mysql_load_statement(table: str, path: Path) -> str:
    file_name = path.as_posix().replace("'", "\\'")
    common = (
        f"LOAD DATA LOCAL INFILE '{file_name}' INTO TABLE {table} "
        "FIELDS TERMINATED BY ',' ENCLOSED BY '\"' "
        "ESCAPED BY '\"' "
        "LINES TERMINATED BY '\\n' IGNORE 1 ROWS"
    )

    if table == "addresses":
        return f"{common} (customer_id, street, city, postcode)"
    if table == "product_details":
        return f"{common} (id, product_id, @specs) SET specs = REPLACE(@specs, '\"\"', '\"')"
    if table == "orders":
        return (
            f"{common} (id, customer_id, @coupon_id, order_date, status, total_price) "
            "SET coupon_id = NULLIF(@coupon_id, '')"
        )
    return common


class MySqlIngestRepository:
    def __init__(self, connection):
        self.connection = connection
        self.cursor = connection.cursor()

    def reset_schema(self) -> None:
        try:
            self.cursor.execute("SET GLOBAL local_infile = 1")
        except mysql.connector.Error:
            pass

        self.cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        for table in reversed(TABLES):
            self.cursor.execute(f"DROP TABLE IF EXISTS {table}")
        self.cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

        schema = MYSQL_SCHEMA_PATH.read_text(encoding="utf-8")
        for statement in split_sql(schema):
            self.cursor.execute(statement)

        self.cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        self.cursor.execute("SET UNIQUE_CHECKS = 0")

    def load_table(self, table: str, csv_path: Path) -> None:
        if table == "product_details":
            self._load_product_details(csv_path)
            return
        self.cursor.execute(mysql_load_statement(table, csv_path))

    def _load_product_details(self, csv_path: Path) -> None:
        with csv_path.open(newline="", encoding="utf-8") as file:
            rows = [(int(row["id"]), int(row["product_id"]), row["specs"]) for row in csv.DictReader(file)]
        self.cursor.executemany(
            "INSERT INTO product_details (id, product_id, specs) VALUES (%s, %s, %s)",
            rows,
        )

    def close(self) -> None:
        self.cursor.execute("SET UNIQUE_CHECKS = 1")
        self.cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        self.connection.commit()
        self.connection.close()
