import json

from benchmarks.scenarios.base import ScenarioDefinition
from benchmarks.scenarios.common import BATCH, MUTATION_BASE_ID, sql_many, sql_scalar, today_iso
from ztbd.config import DatabaseTarget


def sql_c1(adapter) -> dict:
    start_id = sql_scalar(adapter, "SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM customers")
    rows = [
        (start_id + i, f"Bench{i}", "Customer", f"bench-c1-{start_id + i}@example.com", today_iso())
        for i in range(BATCH)
    ]
    return sql_many(
        adapter,
        "INSERT INTO customers (id, first_name, last_name, email, registration_date) VALUES (%s, %s, %s, %s, %s)",
        rows,
    )


def sql_c2(adapter) -> dict:
    next_order = sql_scalar(adapter, "SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM orders")
    next_item = sql_scalar(adapter, "SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM order_items")
    product_id = sql_scalar(adapter, "SELECT MIN(id) AS id FROM products", 1)
    customer_id = sql_scalar(adapter, "SELECT MIN(id) AS id FROM customers", 1)
    affected = 0
    for i in range(BATCH):
        order_id = next_order + i
        affected += adapter.execute(
            "INSERT INTO orders (id, customer_id, coupon_id, order_date, status, total_price) VALUES (%s, %s, NULL, %s, %s, %s)",
            (order_id, customer_id, today_iso(), "paid", 100.0),
        )["rows_affected"]
        affected += adapter.execute(
            "INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) VALUES (%s, %s, %s, %s, %s)",
            (next_item + i, order_id, product_id, 1, 100.0),
        )["rows_affected"]
    return {"rows": [], "rows_affected": affected}


def sql_c3(adapter) -> dict:
    start_id = sql_scalar(adapter, "SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM reviews")
    product_id = sql_scalar(adapter, "SELECT MIN(id) AS id FROM products", 1)
    customer_id = sql_scalar(adapter, "SELECT MIN(id) AS id FROM customers", 1)
    rows = [(start_id + i, product_id, customer_id, 5, "excellent benchmark review") for i in range(BATCH)]
    return sql_many(
        adapter,
        "INSERT INTO reviews (id, product_id, customer_id, rating, comment) VALUES (%s, %s, %s, %s, %s)",
        rows,
    )


def sql_c4(adapter) -> dict:
    start_id = sql_scalar(adapter, "SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM products")
    category_id = sql_scalar(adapter, "SELECT MIN(id) AS id FROM categories", 1)
    supplier_id = sql_scalar(adapter, "SELECT MIN(id) AS id FROM suppliers", 1)
    rows = [(start_id + i, category_id, supplier_id, f"Benchmark Product {start_id + i}", 99.99) for i in range(BATCH)]
    return sql_many(
        adapter,
        "INSERT INTO products (id, category_id, supplier_id, name, price) VALUES (%s, %s, %s, %s, %s)",
        rows,
    )


def sql_c5(adapter) -> dict:
    customer_id = sql_scalar(adapter, "SELECT MIN(id) AS id FROM customers", 1)
    rows = [(customer_id, f"Bench Street {i}", "Bench City", "00000") for i in range(BATCH)]
    return sql_many(adapter, "INSERT INTO addresses (customer_id, street, city, postcode) VALUES (%s, %s, %s, %s)", rows)


def sql_c6(adapter) -> dict:
    next_item = sql_scalar(adapter, "SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM order_items")
    product_id = sql_scalar(adapter, "SELECT MIN(id) AS id FROM products", 1)
    orders = adapter.execute("SELECT id FROM orders ORDER BY id LIMIT 25").get("rows", [])
    rows = [(next_item + i, row["id"], product_id, 1, 42.0) for i, row in enumerate(orders)]
    return sql_many(
        adapter,
        "INSERT INTO order_items (id, order_id, product_id, quantity, unit_price) VALUES (%s, %s, %s, %s, %s)",
        rows,
    )


def mongo_c1(adapter) -> dict:
    docs = [
        {
            "_id": MUTATION_BASE_ID + i,
            "first_name": "Bench",
            "last_name": "Customer",
            "email": f"bench-c1-{i}@example.com",
            "registration_date": today_iso(),
            "addresses": [],
        }
        for i in range(BATCH)
    ]
    adapter.database.customers.insert_many(docs, ordered=False)
    return {"rows": [], "rows_affected": len(docs)}


def mongo_c2(adapter) -> dict:
    docs = [
        {
            "_id": MUTATION_BASE_ID + i,
            "customer_id": 1,
            "order_date": today_iso(),
            "status": "paid",
            "total_price": 100.0,
            "items": [{"id": MUTATION_BASE_ID + i, "product_id": 1, "quantity": 1, "unit_price": 100.0}],
        }
        for i in range(BATCH)
    ]
    adapter.database.orders.insert_many(docs, ordered=False)
    return {"rows": [], "rows_affected": len(docs)}


def mongo_c3(adapter) -> dict:
    docs = [
        {"_id": MUTATION_BASE_ID + i, "product_id": 1, "customer_id": 1, "rating": 5, "comment": "excellent benchmark review"}
        for i in range(BATCH)
    ]
    adapter.database.reviews.insert_many(docs, ordered=False)
    return {"rows": [], "rows_affected": len(docs)}


def mongo_c4(adapter) -> dict:
    docs = [
        {
            "_id": MUTATION_BASE_ID + i,
            "name": f"Benchmark Product {i}",
            "price": 99.99,
            "category": {"id": 1, "name": "Electronics"},
            "supplier": {"id": 1, "name": "Bench"},
            "specs": "Warranty: 2 years",
        }
        for i in range(BATCH)
    ]
    adapter.database.products.insert_many(docs, ordered=False)
    return {"rows": [], "rows_affected": len(docs)}


def mongo_c5(adapter) -> dict:
    result = adapter.database.customers.update_many(
        {},
        {"$push": {"addresses": {"street": "Bench Street", "city": "Bench City", "postcode": "00000"}}},
    )
    return {"rows": [], "rows_affected": result.modified_count}


def mongo_c6(adapter) -> dict:
    result = adapter.database.orders.update_many(
        {},
        {"$push": {"items": {"id": MUTATION_BASE_ID, "product_id": 1, "quantity": 1, "unit_price": 42.0}}},
    )
    return {"rows": [], "rows_affected": result.modified_count}


def redis_c1(adapter) -> dict:
    pipe = adapter.client.pipeline()
    for i in range(BATCH):
        customer_id = MUTATION_BASE_ID + i
        email = f"bench-c1-{i}@example.com"
        pipe.hset(
            f"customer:{customer_id}",
            mapping={"first_name": "Bench", "last_name": "Customer", "email": email, "registration_date": today_iso()},
        )
        pipe.set(f"email:{email}", customer_id)
    pipe.execute()
    return {"rows": [], "rows_affected": BATCH}


def redis_c2(adapter) -> dict:
    pipe = adapter.client.pipeline()
    for i in range(BATCH):
        pipe.set(
            f"order:{MUTATION_BASE_ID + i}",
            json.dumps({"_id": MUTATION_BASE_ID + i, "customer_id": 1, "items": [{"product_id": 1, "quantity": 1, "unit_price": 100.0}]}),
        )
    pipe.execute()
    return {"rows": [], "rows_affected": BATCH}


def redis_c3(adapter) -> dict:
    pipe = adapter.client.pipeline()
    for i in range(BATCH):
        review_id = MUTATION_BASE_ID + i
        pipe.hset(
            f"review:{review_id}",
            mapping={"product_id": "1", "customer_id": "1", "rating": "5", "comment": "excellent benchmark review"},
        )
        pipe.lpush("product:1:reviews", review_id)
    pipe.execute()
    return {"rows": [], "rows_affected": BATCH}


def redis_c4(adapter) -> dict:
    pipe = adapter.client.pipeline()
    for i in range(BATCH):
        pipe.hset(
            f"product:{MUTATION_BASE_ID + i}",
            mapping={
                "name": f"Benchmark Product {i}",
                "price": "99.99",
                "category_name": "Electronics",
                "supplier_name": "Bench",
                "specs": "Warranty: 2 years",
            },
        )
    pipe.execute()
    return {"rows": [], "rows_affected": BATCH}


def redis_c5(adapter) -> dict:
    adapter.client.set("customer:1:addresses", json.dumps([{"street": "Bench Street", "city": "Bench City", "postcode": "00000"}]))
    return {"rows": [], "rows_affected": 1}


CREATE_SCENARIOS = {
    "c1": ScenarioDefinition("c1", "Batch insert customers", {DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO, DatabaseTarget.REDIS}, {DatabaseTarget.MYSQL: sql_c1, DatabaseTarget.POSTGRES: sql_c1, DatabaseTarget.MONGO: mongo_c1, DatabaseTarget.REDIS: redis_c1}, mutating=True),
    "c2": ScenarioDefinition("c2", "Insert order with items", {DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO, DatabaseTarget.REDIS}, {DatabaseTarget.MYSQL: sql_c2, DatabaseTarget.POSTGRES: sql_c2, DatabaseTarget.MONGO: mongo_c2, DatabaseTarget.REDIS: redis_c2}, mutating=True),
    "c3": ScenarioDefinition("c3", "Append reviews", {DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO, DatabaseTarget.REDIS}, {DatabaseTarget.MYSQL: sql_c3, DatabaseTarget.POSTGRES: sql_c3, DatabaseTarget.MONGO: mongo_c3, DatabaseTarget.REDIS: redis_c3}, mutating=True),
    "c4": ScenarioDefinition("c4", "Insert products", {DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO, DatabaseTarget.REDIS}, {DatabaseTarget.MYSQL: sql_c4, DatabaseTarget.POSTGRES: sql_c4, DatabaseTarget.MONGO: mongo_c4, DatabaseTarget.REDIS: redis_c4}, mutating=True),
    "c5": ScenarioDefinition("c5", "Insert addresses", {DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO, DatabaseTarget.REDIS}, {DatabaseTarget.MYSQL: sql_c5, DatabaseTarget.POSTGRES: sql_c5, DatabaseTarget.MONGO: mongo_c5, DatabaseTarget.REDIS: redis_c5}, mutating=True),
    "c6": ScenarioDefinition("c6", "Insert order items with coupon context", {DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO}, {DatabaseTarget.MYSQL: sql_c6, DatabaseTarget.POSTGRES: sql_c6, DatabaseTarget.MONGO: mongo_c6}, mutating=True),
}
