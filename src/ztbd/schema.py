from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from ztbd.config import PROJECT_ROOT


TABLES = [
    "categories",
    "suppliers",
    "coupons",
    "customers",
    "products",
    "addresses",
    "product_details",
    "orders",
    "order_items",
    "reviews",
]

LOAD_ORDER = [
    "categories",
    "suppliers",
    "coupons",
    "customers",
    "products",
    "addresses",
    "product_details",
    "orders",
    "order_items",
    "reviews",
]

CSV_COLUMNS = {
    "categories": ["id", "name"],
    "suppliers": ["id", "name", "country", "phone"],
    "coupons": ["id", "code", "discount_pct"],
    "customers": ["id", "first_name", "last_name", "email", "registration_date"],
    "products": ["id", "category_id", "supplier_id", "name", "price"],
    "addresses": ["customer_id", "street", "city", "postcode"],
    "product_details": ["id", "product_id", "specs"],
    "orders": ["id", "customer_id", "coupon_id", "order_date", "status", "total_price"],
    "order_items": ["id", "order_id", "product_id", "quantity", "unit_price"],
    "reviews": ["id", "product_id", "customer_id", "rating", "comment"],
}

MYSQL_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "mysql_schema.sql"
POSTGRES_SCHEMA_PATH = PROJECT_ROOT / "schemas" / "postgre_schema.sql"


@dataclass(frozen=True)
class LoadPlan:
    tables: list[str]
    columns: dict[str, list[str]]

    def csv_path(self, data_dir: Path, table: str) -> Path:
        return data_dir / f"{table}.csv"

    def validate_files(self, data_dir: Path) -> None:
        missing = [str(self.csv_path(data_dir, table)) for table in self.tables if not self.csv_path(data_dir, table).exists()]
        if missing:
            raise FileNotFoundError("Missing CSV files:\n" + "\n".join(missing))


DEFAULT_LOAD_PLAN = LoadPlan(tables=LOAD_ORDER, columns=CSV_COLUMNS)


def split_sql(sql: str) -> Iterable[str]:
    for statement in sql.split(";"):
        statement = statement.strip()
        if statement:
            yield statement
