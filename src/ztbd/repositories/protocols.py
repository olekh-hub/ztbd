from pathlib import Path
from typing import Protocol


class RelationalIngestRepository(Protocol):
    def reset_schema(self) -> None:
        ...

    def load_table(self, table: str, csv_path: Path) -> None:
        ...

    def close(self) -> None:
        ...


class DocumentRepository(Protocol):
    def reset(self) -> None:
        ...

    def insert_customers(self, customers: list[dict]) -> None:
        ...

    def insert_products(self, products: list[dict]) -> None:
        ...

    def insert_reviews(self, reviews: list[dict]) -> None:
        ...

    def insert_orders(self, orders: list[dict]) -> None:
        ...


class KeyValueRepository(Protocol):
    def reset(self) -> None:
        ...

    def put_customers(self, customers: list[dict]) -> None:
        ...

    def put_products(self, products: list[dict]) -> None:
        ...

    def put_reviews(self, reviews: list[dict]) -> None:
        ...

    def put_orders(self, orders: list[dict]) -> None:
        ...
