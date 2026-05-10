from typing import Any

from benchmarks.scenarios.base import ScenarioDefinition
from ztbd.config import DatabaseTarget


MYSQL_R1 = "SELECT * FROM customers WHERE email = (SELECT email FROM (SELECT email FROM customers ORDER BY id LIMIT 1) c)"
POSTGRES_R1 = "SELECT * FROM customers WHERE email = (SELECT email FROM customers ORDER BY id LIMIT 1)"
R2_SQL = (
    "SELECT id, customer_id, total_price FROM orders "
    "WHERE order_date BETWEEN '2026-01-01' AND '2026-01-07' ORDER BY order_date"
)
R3_SQL = """
SELECT c.id, c.last_name, SUM(oi.quantity * oi.unit_price) AS total
FROM customers c
JOIN orders o ON o.customer_id = c.id
JOIN order_items oi ON oi.order_id = o.id
GROUP BY c.id, c.last_name
ORDER BY total DESC
LIMIT 10
"""
R4_SQL = """
SELECT cat.name, SUM(oi.quantity * oi.unit_price) AS revenue
FROM order_items oi
JOIN products p ON p.id = oi.product_id
JOIN categories cat ON cat.id = p.category_id
GROUP BY cat.name
"""
MYSQL_R5 = "SELECT * FROM reviews WHERE comment LIKE '%excellent%'"
POSTGRES_R5 = "SELECT * FROM reviews WHERE comment ILIKE '%excellent%'"
R6_SQL = """
SELECT p.id, p.name, AVG(r.rating) avg_r, COUNT(*) cnt
FROM products p
JOIN reviews r ON r.product_id = p.id
WHERE p.category_id = 1
GROUP BY p.id, p.name
HAVING COUNT(*) >= 100
ORDER BY avg_r DESC
LIMIT 20
"""


def sql_query(query: str):
    def operation(adapter) -> dict:
        return adapter.execute(query)

    return operation


def sql_explain(query: str):
    def explain(adapter) -> str | None:
        return adapter.explain(query)

    return explain


def mongo_explain(adapter, collection: str, pipeline: list[dict]) -> str:
    return str(
        adapter.database.command(
            "explain",
            {"aggregate": collection, "pipeline": pipeline, "cursor": {}},
            verbosity="executionStats",
        )
    )


def mongo_result(rows: list[dict]) -> dict:
    return {"rows": rows, "rows_affected": len(rows)}


def mongo_r1(adapter) -> dict:
    customer = adapter.database.customers.find_one({}, sort=[("_id", 1)])
    if customer is None:
        return mongo_result([])
    return mongo_result(list(adapter.database.customers.find({"email": customer["email"]})))


def mongo_r1_explain(adapter) -> str | None:
    customer = adapter.database.customers.find_one({}, sort=[("_id", 1)])
    if customer is None:
        return None
    return str(adapter.database.customers.find({"email": customer["email"]}).explain())


def redis_r1(adapter) -> dict:
    email = adapter.client.hget("customer:1", "email")
    if not email:
        return {"rows": [], "rows_affected": 0}
    customer_id = adapter.client.get(f"email:{email}")
    if not customer_id:
        return {"rows": [], "rows_affected": 0}
    customer = adapter.client.hgetall(f"customer:{customer_id}")
    return {"rows": [customer] if customer else [], "rows_affected": 1 if customer else 0}


def mongo_r2_pipeline() -> list[dict]:
    return [
        {"$match": {"order_date": {"$gte": "2026-01-01", "$lte": "2026-01-07"}}},
        {"$sort": {"order_date": 1}},
        {"$project": {"_id": 1, "customer_id": 1, "total_price": 1}},
    ]


def mongo_r2(adapter) -> dict:
    return mongo_result(list(adapter.database.orders.aggregate(mongo_r2_pipeline())))


def mongo_r2_explain(adapter) -> str:
    return mongo_explain(adapter, "orders", mongo_r2_pipeline())


def mongo_r3_pipeline() -> list[dict]:
    return [
        {"$unwind": "$items"},
        {
            "$group": {
                "_id": "$customer_id",
                "total": {"$sum": {"$multiply": ["$items.quantity", "$items.unit_price"]}},
            }
        },
        {"$sort": {"total": -1}},
        {"$limit": 10},
        {"$lookup": {"from": "customers", "localField": "_id", "foreignField": "_id", "as": "customer"}},
        {"$unwind": {"path": "$customer", "preserveNullAndEmptyArrays": True}},
        {"$project": {"customer_id": "$_id", "last_name": "$customer.last_name", "total": 1}},
    ]


def mongo_r3(adapter) -> dict:
    return mongo_result(list(adapter.database.orders.aggregate(mongo_r3_pipeline())))


def mongo_r3_explain(adapter) -> str:
    return mongo_explain(adapter, "orders", mongo_r3_pipeline())


def mongo_r4_pipeline() -> list[dict]:
    return [
        {"$unwind": "$items"},
        {"$lookup": {"from": "products", "localField": "items.product_id", "foreignField": "_id", "as": "product"}},
        {"$unwind": "$product"},
        {
            "$group": {
                "_id": "$product.category.name",
                "revenue": {"$sum": {"$multiply": ["$items.quantity", "$items.unit_price"]}},
            }
        },
        {"$project": {"category": "$_id", "revenue": 1, "_id": 0}},
    ]


def mongo_r4(adapter) -> dict:
    return mongo_result(list(adapter.database.orders.aggregate(mongo_r4_pipeline())))


def mongo_r4_explain(adapter) -> str:
    return mongo_explain(adapter, "orders", mongo_r4_pipeline())


def mongo_r5(adapter) -> dict:
    return mongo_result(list(adapter.database.reviews.find({"comment": {"$regex": "excellent", "$options": "i"}})))


def mongo_r5_explain(adapter) -> str:
    return str(adapter.database.reviews.find({"comment": {"$regex": "excellent", "$options": "i"}}).explain())


def mongo_r6_pipeline() -> list[dict]:
    return [
        {"$match": {"category.name": "Electronics"}},
        {"$lookup": {"from": "reviews", "localField": "_id", "foreignField": "product_id", "as": "reviews"}},
        {"$unwind": "$reviews"},
        {
            "$group": {
                "_id": {"id": "$_id", "name": "$name"},
                "avg_r": {"$avg": "$reviews.rating"},
                "cnt": {"$sum": 1},
            }
        },
        {"$match": {"cnt": {"$gte": 100}}},
        {"$sort": {"avg_r": -1}},
        {"$limit": 20},
        {"$project": {"id": "$_id.id", "name": "$_id.name", "avg_r": 1, "cnt": 1, "_id": 0}},
    ]


def mongo_r6(adapter) -> dict:
    return mongo_result(list(adapter.database.products.aggregate(mongo_r6_pipeline())))


def mongo_r6_explain(adapter) -> str:
    return mongo_explain(adapter, "products", mongo_r6_pipeline())


READ_SCENARIOS: dict[str, ScenarioDefinition] = {
    "r1": ScenarioDefinition(
        scenario_id="r1",
        name="Point lookup customer by email",
        supported_targets={DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO, DatabaseTarget.REDIS},
        operation_by_target={
            DatabaseTarget.MYSQL: sql_query(MYSQL_R1),
            DatabaseTarget.POSTGRES: sql_query(POSTGRES_R1),
            DatabaseTarget.MONGO: mongo_r1,
            DatabaseTarget.REDIS: redis_r1,
        },
        explain_by_target={
            DatabaseTarget.MYSQL: sql_explain(MYSQL_R1),
            DatabaseTarget.POSTGRES: sql_explain(POSTGRES_R1),
            DatabaseTarget.MONGO: mongo_r1_explain,
        },
    ),
    "r2": ScenarioDefinition(
        scenario_id="r2",
        name="Date range lookup for orders",
        supported_targets={DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO},
        operation_by_target={
            DatabaseTarget.MYSQL: sql_query(R2_SQL),
            DatabaseTarget.POSTGRES: sql_query(R2_SQL),
            DatabaseTarget.MONGO: mongo_r2,
        },
        explain_by_target={
            DatabaseTarget.MYSQL: sql_explain(R2_SQL),
            DatabaseTarget.POSTGRES: sql_explain(R2_SQL),
            DatabaseTarget.MONGO: mongo_r2_explain,
        },
    ),
    "r3": ScenarioDefinition(
        scenario_id="r3",
        name="Top customers by spend",
        supported_targets={DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO},
        operation_by_target={
            DatabaseTarget.MYSQL: sql_query(R3_SQL),
            DatabaseTarget.POSTGRES: sql_query(R3_SQL),
            DatabaseTarget.MONGO: mongo_r3,
        },
        explain_by_target={
            DatabaseTarget.MYSQL: sql_explain(R3_SQL),
            DatabaseTarget.POSTGRES: sql_explain(R3_SQL),
            DatabaseTarget.MONGO: mongo_r3_explain,
        },
    ),
    "r4": ScenarioDefinition(
        scenario_id="r4",
        name="Revenue by product category",
        supported_targets={DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO},
        operation_by_target={
            DatabaseTarget.MYSQL: sql_query(R4_SQL),
            DatabaseTarget.POSTGRES: sql_query(R4_SQL),
            DatabaseTarget.MONGO: mongo_r4,
        },
        explain_by_target={
            DatabaseTarget.MYSQL: sql_explain(R4_SQL),
            DatabaseTarget.POSTGRES: sql_explain(R4_SQL),
            DatabaseTarget.MONGO: mongo_r4_explain,
        },
    ),
    "r5": ScenarioDefinition(
        scenario_id="r5",
        name="Search review comments",
        supported_targets={DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO},
        operation_by_target={
            DatabaseTarget.MYSQL: sql_query(MYSQL_R5),
            DatabaseTarget.POSTGRES: sql_query(POSTGRES_R5),
            DatabaseTarget.MONGO: mongo_r5,
        },
        explain_by_target={
            DatabaseTarget.MYSQL: sql_explain(MYSQL_R5),
            DatabaseTarget.POSTGRES: sql_explain(POSTGRES_R5),
            DatabaseTarget.MONGO: mongo_r5_explain,
        },
    ),
    "r6": ScenarioDefinition(
        scenario_id="r6",
        name="Top rated products in Electronics",
        supported_targets={DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO},
        operation_by_target={
            DatabaseTarget.MYSQL: sql_query(R6_SQL),
            DatabaseTarget.POSTGRES: sql_query(R6_SQL),
            DatabaseTarget.MONGO: mongo_r6,
        },
        explain_by_target={
            DatabaseTarget.MYSQL: sql_explain(R6_SQL),
            DatabaseTarget.POSTGRES: sql_explain(R6_SQL),
            DatabaseTarget.MONGO: mongo_r6_explain,
        },
    ),
}
