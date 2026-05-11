import random

from faker import Faker

from ztbd.config import AppSettings, DatabaseTarget, SIZE_PROFILES
from ztbd.csv_store import CsvStore
from ztbd.generation import DataGenerator
from ztbd.ingestion import IngestionService


class FakeRelationalRepository:
    def __init__(self):
        self.calls = []

    def reset_schema(self) -> None:
        self.calls.append(("reset_schema",))

    def load_table(self, table, csv_path) -> None:
        self.calls.append(("load_table", table, csv_path.name))

    def close(self) -> None:
        self.calls.append(("close",))


class FakeDocumentRepository:
    def __init__(self):
        self.calls = []

    def reset(self) -> None:
        self.calls.append(("reset",))

    def insert_customers(self, customers) -> None:
        self.calls.append(("customers", len(customers)))

    def insert_products(self, products) -> None:
        self.calls.append(("products", len(products)))

    def insert_reviews(self, reviews) -> None:
        self.calls.append(("reviews", len(reviews)))

    def insert_orders(self, orders) -> None:
        self.calls.append(("orders", len(orders)))


class FakeKeyValueRepository(FakeDocumentRepository):
    def put_customers(self, customers) -> None:
        self.calls.append(("customers", len(customers)))

    def put_products(self, products) -> None:
        self.calls.append(("products", len(products)))

    def put_reviews(self, reviews) -> None:
        self.calls.append(("reviews", len(reviews)))

    def put_orders(self, orders) -> None:
        self.calls.append(("orders", len(orders)))


def generate_fixture(tmp_path) -> CsvStore:
    fake = Faker("en_US")
    fake.seed_instance(7)
    store = CsvStore(tmp_path)
    DataGenerator(SIZE_PROFILES["test"], store, fake, random.Random(7)).generate()
    return store


def test_ingestion_service_loads_relational_tables_in_order(tmp_path) -> None:
    store = generate_fixture(tmp_path)
    repo = FakeRelationalRepository()
    service = IngestionService(
        settings=AppSettings(data_dir=tmp_path),
        store=store,
        relational_repositories={DatabaseTarget.MYSQL: repo},
    )

    service.run({DatabaseTarget.MYSQL})

    assert repo.calls[0] == ("reset_schema",)
    assert repo.calls[1] == ("load_table", "categories", "categories.csv")
    assert repo.calls[-1] == ("close",)


def test_ingestion_service_injects_document_and_key_value_repositories(tmp_path) -> None:
    store = generate_fixture(tmp_path)
    document_repo = FakeDocumentRepository()
    key_value_repo = FakeKeyValueRepository()
    service = IngestionService(
        settings=AppSettings(data_dir=tmp_path, order_batch_size=4),
        store=store,
        document_repository=document_repo,
        key_value_repository=key_value_repo,
    )

    service.run({DatabaseTarget.MONGO, DatabaseTarget.REDIS})

    assert ("customers", SIZE_PROFILES["test"].customers) in document_repo.calls
    assert ("reviews", SIZE_PROFILES["test"].reviews) in key_value_repo.calls
    assert ("orders", 4) in document_repo.calls


def test_ingestion_service_populates_and_reuses_static_frames_cache(tmp_path) -> None:
    store = generate_fixture(tmp_path)
    cache: dict = {}

    document_repo_first = FakeDocumentRepository()
    IngestionService(
        settings=AppSettings(data_dir=tmp_path, order_batch_size=4),
        store=store,
        document_repository=document_repo_first,
        static_frames=cache,
    ).run({DatabaseTarget.MONGO})

    assert "customers" in cache and "products" in cache and "reviews" in cache

    sentinel_frame = cache["customers"]
    cache["customers"] = sentinel_frame
    document_repo_second = FakeDocumentRepository()
    IngestionService(
        settings=AppSettings(data_dir=tmp_path, order_batch_size=4),
        store=store,
        document_repository=document_repo_second,
        static_frames=cache,
    ).run({DatabaseTarget.MONGO})

    assert cache["customers"] is sentinel_frame
