import json


PIPELINE_BATCH = 5_000


class RedisKeyValueRepository:
    def __init__(self, client):
        self.client = client

    def close(self) -> None:
        self.client.close()

    def reset(self) -> None:
        self.client.flushdb()

    def put_customers(self, customers: list[dict]) -> None:
        for start in range(0, len(customers), PIPELINE_BATCH):
            pipeline = self.client.pipeline(transaction=False)
            for customer in customers[start : start + PIPELINE_BATCH]:
                pipeline.hset(
                    f'customer:{customer["_id"]}',
                    mapping={
                        "first_name": str(customer["first_name"]),
                        "last_name": str(customer["last_name"]),
                        "email": str(customer["email"]),
                        "registration_date": str(customer["registration_date"]),
                    },
                )
                pipeline.set(f'email:{customer["email"]}', customer["_id"])
                pipeline.set(f'customer:{customer["_id"]}:addresses', json.dumps(customer["addresses"], default=str))
            pipeline.execute()

    def put_products(self, products: list[dict]) -> None:
        for start in range(0, len(products), PIPELINE_BATCH):
            pipeline = self.client.pipeline(transaction=False)
            for product in products[start : start + PIPELINE_BATCH]:
                pipeline.hset(
                    f'product:{product["_id"]}',
                    mapping={
                        "name": str(product["name"]),
                        "price": str(product["price"]),
                        "category_name": str(product.get("category", {}).get("name", "")),
                        "supplier_name": str(product.get("supplier", {}).get("name", "")),
                        "specs": str(product["specs"]),
                    },
                )
            pipeline.execute()

    def put_reviews(self, reviews: list[dict]) -> None:
        for start in range(0, len(reviews), PIPELINE_BATCH):
            pipeline = self.client.pipeline(transaction=False)
            for review in reviews[start : start + PIPELINE_BATCH]:
                pipeline.hset(
                    f"review:{review['_id']}",
                    mapping={
                        "product_id": str(review["product_id"]),
                        "customer_id": str(review["customer_id"]),
                        "rating": str(review["rating"]),
                        "comment": str(review["comment"]),
                    },
                )
                pipeline.lpush(f"product:{review['product_id']}:reviews", review["_id"])
            pipeline.execute()

    def put_orders(self, orders: list[dict]) -> None:
        for start in range(0, len(orders), PIPELINE_BATCH):
            pipeline = self.client.pipeline(transaction=False)
            for order in orders[start : start + PIPELINE_BATCH]:
                pipeline.set(f'order:{order["_id"]}', json.dumps(order, default=str))
            pipeline.execute()
