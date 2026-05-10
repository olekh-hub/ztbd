from benchmarks.scenarios.base import ScenarioDefinition
from benchmarks.scenarios.common import sql_one
from ztbd.config import DatabaseTarget


def sql_u1(adapter) -> dict:
    email_row = sql_one(adapter, "SELECT email FROM customers ORDER BY id LIMIT 1")
    if not email_row:
        return {"rows": [], "rows_affected": 0}
    return adapter.execute("UPDATE customers SET last_name = %s WHERE email = %s", ("Updated", email_row["email"]))


def sql_u2(adapter) -> dict:
    return adapter.execute("UPDATE orders SET status = %s WHERE status = %s", ("delivered", "shipped"))


def sql_u3(adapter) -> dict:
    return adapter.execute("UPDATE products SET price = price * 1.10 WHERE category_id = 1")


def mysql_u4(adapter) -> dict:
    return adapter.execute("UPDATE product_details SET specs = JSON_SET(specs, '$.warranty', %s)", ("3 years",))


def postgres_u4(adapter) -> dict:
    return adapter.execute("UPDATE product_details SET specs = jsonb_set(specs, '{warranty}', %s::jsonb, true)", ('"3 years"',))


def sql_u5(adapter) -> dict:
    item = sql_one(adapter, "SELECT id, order_id FROM order_items ORDER BY id LIMIT 1")
    if not item:
        return {"rows": [], "rows_affected": 0}
    affected = adapter.execute("UPDATE order_items SET quantity = quantity + 1 WHERE id = %s", (item["id"],))["rows_affected"]
    affected += adapter.execute(
        "UPDATE orders SET total_price = (SELECT COALESCE(SUM(quantity * unit_price), 0) FROM order_items WHERE order_id = %s) WHERE id = %s",
        (item["order_id"], item["order_id"]),
    )["rows_affected"]
    return {"rows": [], "rows_affected": affected}


def sql_u6(adapter) -> dict:
    return adapter.execute("UPDATE orders SET coupon_id = NULL WHERE coupon_id IS NOT NULL")


def mongo_u1(adapter) -> dict:
    customer = adapter.database.customers.find_one({}, sort=[("_id", 1)])
    result = adapter.database.customers.update_one({"email": customer["email"]}, {"$set": {"last_name": "Updated"}}) if customer else None
    return {"rows": [], "rows_affected": result.modified_count if result else 0}


def mongo_u2(adapter) -> dict:
    result = adapter.database.orders.update_many({"status": "shipped"}, {"$set": {"status": "delivered"}})
    return {"rows": [], "rows_affected": result.modified_count}


def mongo_u3(adapter) -> dict:
    result = adapter.database.products.update_many({"category.name": "Electronics"}, {"$mul": {"price": 1.10}})
    return {"rows": [], "rows_affected": result.modified_count}


def mongo_u4(adapter) -> dict:
    result = adapter.database.products.update_many({}, {"$set": {"specs": {"warranty": "3 years"}}})
    return {"rows": [], "rows_affected": result.modified_count}


def mongo_u5(adapter) -> dict:
    order = adapter.database.orders.find_one({"items.0": {"$exists": True}}, sort=[("_id", 1)])
    if not order:
        return {"rows": [], "rows_affected": 0}
    items = order["items"]
    items[0]["quantity"] = int(items[0].get("quantity", 1)) + 1
    total = sum(float(item.get("quantity", 0)) * float(item.get("unit_price", 0)) for item in items)
    result = adapter.database.orders.update_one({"_id": order["_id"]}, {"$set": {"items": items, "total_price": total}})
    return {"rows": [], "rows_affected": result.modified_count}


def mongo_u6(adapter) -> dict:
    result = adapter.database.orders.update_many({"coupon": {"$exists": True}}, {"$unset": {"coupon": ""}})
    return {"rows": [], "rows_affected": result.modified_count}


def redis_u1(adapter) -> dict:
    email = adapter.client.hget("customer:1", "email")
    customer_id = adapter.client.get(f"email:{email}") if email else None
    if not customer_id:
        return {"rows": [], "rows_affected": 0}
    return {"rows": [], "rows_affected": adapter.client.hset(f"customer:{customer_id}", "last_name", "Updated")}


def redis_u4(adapter) -> dict:
    return {"rows": [], "rows_affected": adapter.client.hset("product:1", "specs", '{"warranty":"3 years"}')}


UPDATE_SCENARIOS = {
    "u1": ScenarioDefinition("u1", "Point update customer by email", {DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO, DatabaseTarget.REDIS}, {DatabaseTarget.MYSQL: sql_u1, DatabaseTarget.POSTGRES: sql_u1, DatabaseTarget.MONGO: mongo_u1, DatabaseTarget.REDIS: redis_u1}, mutating=True),
    "u2": ScenarioDefinition("u2", "Batch update shipped orders", {DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO}, {DatabaseTarget.MYSQL: sql_u2, DatabaseTarget.POSTGRES: sql_u2, DatabaseTarget.MONGO: mongo_u2}, mutating=True),
    "u3": ScenarioDefinition("u3", "Increase product prices in category", {DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO}, {DatabaseTarget.MYSQL: sql_u3, DatabaseTarget.POSTGRES: sql_u3, DatabaseTarget.MONGO: mongo_u3}, mutating=True),
    "u4": ScenarioDefinition("u4", "Update semi-structured specs", {DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO, DatabaseTarget.REDIS}, {DatabaseTarget.MYSQL: mysql_u4, DatabaseTarget.POSTGRES: postgres_u4, DatabaseTarget.MONGO: mongo_u4, DatabaseTarget.REDIS: redis_u4}, mutating=True),
    "u5": ScenarioDefinition("u5", "Recalculate order total after item edit", {DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO}, {DatabaseTarget.MYSQL: sql_u5, DatabaseTarget.POSTGRES: sql_u5, DatabaseTarget.MONGO: mongo_u5}, mutating=True),
    "u6": ScenarioDefinition("u6", "Remove coupon references from orders", {DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO}, {DatabaseTarget.MYSQL: sql_u6, DatabaseTarget.POSTGRES: sql_u6, DatabaseTarget.MONGO: mongo_u6}, mutating=True),
}
