class MongoDocumentRepository:
    def __init__(self, database, batch_size: int = 5_000):
        self.database = database
        self.batch_size = batch_size

    def reset(self) -> None:
        for collection in ["customers", "products", "orders", "reviews"]:
            self.database[collection].drop()

    def insert_customers(self, customers: list[dict]) -> None:
        self._insert_many("customers", customers)

    def insert_products(self, products: list[dict]) -> None:
        self._insert_many("products", products)

    def insert_reviews(self, reviews: list[dict]) -> None:
        self._insert_many("reviews", reviews)

    def insert_orders(self, orders: list[dict]) -> None:
        self._insert_many("orders", orders)

    def _insert_many(self, collection: str, docs: list[dict]) -> None:
        if not docs:
            return
        for start in range(0, len(docs), self.batch_size):
            self.database[collection].insert_many(docs[start : start + self.batch_size])
