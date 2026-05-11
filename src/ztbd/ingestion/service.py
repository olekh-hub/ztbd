from ztbd.config import AppSettings, DatabaseTarget
from ztbd.csv_store import CsvStore
from ztbd.ingestion.transforms import build_customers, build_products, build_reviews, iter_orders, read_static_frames
from ztbd.repositories.protocols import DocumentRepository, KeyValueRepository, RelationalIngestRepository
from ztbd.schema import DEFAULT_LOAD_PLAN


class IngestionService:
    def __init__(
        self,
        settings: AppSettings,
        store: CsvStore,
        relational_repositories: dict[DatabaseTarget, RelationalIngestRepository] | None = None,
        document_repository: DocumentRepository | None = None,
        key_value_repository: KeyValueRepository | None = None,
        static_frames: dict | None = None,
    ):
        self.settings = settings
        self.store = store
        self.relational_repositories = relational_repositories or {}
        self.document_repository = document_repository
        self.key_value_repository = key_value_repository
        self.static_frames = static_frames

    def run(self, targets: set[DatabaseTarget]) -> None:
        self.store.validate()

        for target in [DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES]:
            if target in targets:
                self._ingest_relational(target)

        if DatabaseTarget.MONGO in targets or DatabaseTarget.REDIS in targets:
            self._ingest_document_stores(use_mongo=DatabaseTarget.MONGO in targets, use_redis=DatabaseTarget.REDIS in targets)

    def _ingest_relational(self, target: DatabaseTarget) -> None:
        repository = self.relational_repositories[target]
        print(f"Ingesting {target.value}")
        try:
            repository.reset_schema()
            for table in DEFAULT_LOAD_PLAN.tables:
                repository.load_table(table, self.store.path_for(table))
                print(f"  loaded {table}")
        finally:
            repository.close()

    def _ingest_document_stores(self, use_mongo: bool, use_redis: bool) -> None:
        print("Ingesting document/key-value stores")
        if self.static_frames is not None and self.static_frames:
            frames = self.static_frames
        else:
            frames = read_static_frames(self.store)
            if self.static_frames is not None:
                self.static_frames.update(frames)

        if use_mongo and self.document_repository is not None:
            self.document_repository.reset()
        if use_redis and self.key_value_repository is not None:
            self.key_value_repository.reset()

        customers = build_customers(frames)
        products = build_products(frames)
        reviews = build_reviews(frames)

        if use_mongo and self.document_repository is not None:
            self.document_repository.insert_customers(customers)
            self.document_repository.insert_products(products)
            self.document_repository.insert_reviews(reviews)
        if use_redis and self.key_value_repository is not None:
            self.key_value_repository.put_customers(customers)
            self.key_value_repository.put_products(products)
            self.key_value_repository.put_reviews(reviews)

        for orders in iter_orders(self.store, frames, self.settings.order_batch_size):
            if use_mongo and self.document_repository is not None:
                self.document_repository.insert_orders(orders)
            if use_redis and self.key_value_repository is not None:
                self.key_value_repository.put_orders(orders)
            print(f"  imported {len(orders)} orders")
