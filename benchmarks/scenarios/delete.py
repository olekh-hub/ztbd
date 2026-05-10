import json

from benchmarks.scenarios.base import ScenarioDefinition
from benchmarks.scenarios.common import sql_one, sql_scalar
from ztbd.config import DatabaseTarget


def sql_d1(adapter) -> dict:
    customer_id = sql_scalar(adapter, "SELECT MIN(id) AS id FROM customers", 0)
    if customer_id == 0:
        return {"rows": [], "rows_affected": 0}
    affected = adapter.execute("DELETE FROM addresses WHERE customer_id = %s", (customer_id,))["rows_affected"]
    affected += adapter.execute("DELETE FROM reviews WHERE customer_id = %s", (customer_id,))["rows_affected"]
    affected += adapter.execute("UPDATE orders SET customer_id = NULL WHERE customer_id = %s", (customer_id,))["rows_affected"]
    affected += adapter.execute("DELETE FROM customers WHERE id = %s", (customer_id,))["rows_affected"]
    return {"rows": [], "rows_affected": affected}


def sql_d2(adapter) -> dict:
    orders = adapter.execute("SELECT id FROM orders WHERE status = 'cancelled' LIMIT 25").get("rows", [])
    if not orders:
        return {"rows": [], "rows_affected": 0}
    order_ids = [row["id"] for row in orders]
    placeholders = ", ".join(["%s"] * len(order_ids))
    affected = adapter.execute(f"DELETE FROM order_items WHERE order_id IN ({placeholders})", tuple(order_ids))["rows_affected"]
    affected += adapter.execute(f"DELETE FROM orders WHERE id IN ({placeholders})", tuple(order_ids))["rows_affected"]
    return {"rows": [], "rows_affected": affected}


def sql_d3(adapter) -> dict:
    product_id = sql_scalar(adapter, "SELECT MIN(id) AS id FROM products", 1)
    return adapter.execute("DELETE FROM reviews WHERE product_id = %s AND rating = 1", (product_id,))


def sql_d4(adapter) -> dict:
    item = sql_one(adapter, "SELECT order_id, product_id FROM order_items ORDER BY id LIMIT 1")
    if not item:
        return {"rows": [], "rows_affected": 0}
    return adapter.execute("DELETE FROM order_items WHERE order_id = %s AND product_id = %s", (item["order_id"], item["product_id"]))


def sql_d5(adapter) -> dict:
    products = adapter.execute("SELECT id FROM products WHERE category_id = 5 LIMIT 25").get("rows", [])
    if not products:
        return {"rows": [], "rows_affected": 0}
    product_ids = [row["id"] for row in products]
    placeholders = ", ".join(["%s"] * len(product_ids))
    affected = adapter.execute(f"DELETE FROM product_details WHERE product_id IN ({placeholders})", tuple(product_ids))["rows_affected"]
    affected += adapter.execute(f"DELETE FROM order_items WHERE product_id IN ({placeholders})", tuple(product_ids))["rows_affected"]
    affected += adapter.execute(f"DELETE FROM reviews WHERE product_id IN ({placeholders})", tuple(product_ids))["rows_affected"]
    affected += adapter.execute(f"DELETE FROM products WHERE id IN ({placeholders})", tuple(product_ids))["rows_affected"]
    return {"rows": [], "rows_affected": affected}


def sql_d6(adapter) -> dict:
    coupons = adapter.execute("SELECT id FROM coupons ORDER BY id LIMIT 20").get("rows", [])
    if not coupons:
        return {"rows": [], "rows_affected": 0}
    coupon_ids = [row["id"] for row in coupons]
    placeholders = ", ".join(["%s"] * len(coupon_ids))
    affected = adapter.execute(f"UPDATE orders SET coupon_id = NULL WHERE coupon_id IN ({placeholders})", tuple(coupon_ids))["rows_affected"]
    affected += adapter.execute(f"DELETE FROM coupons WHERE id IN ({placeholders})", tuple(coupon_ids))["rows_affected"]
    return {"rows": [], "rows_affected": affected}


def mongo_d1(adapter) -> dict:
    customer = adapter.database.customers.find_one({}, sort=[("_id", 1)])
    if not customer:
        return {"rows": [], "rows_affected": 0}
    affected = adapter.database.reviews.delete_many({"customer_id": customer["_id"]}).deleted_count
    affected += adapter.database.customers.delete_one({"_id": customer["_id"]}).deleted_count
    return {"rows": [], "rows_affected": affected}


def mongo_d2(adapter) -> dict:
    result = adapter.database.orders.delete_many({"status": "cancelled"})
    return {"rows": [], "rows_affected": result.deleted_count}


def mongo_d3(adapter) -> dict:
    result = adapter.database.reviews.delete_many({"product_id": 1, "rating": 1})
    return {"rows": [], "rows_affected": result.deleted_count}


def mongo_d4(adapter) -> dict:
    result = adapter.database.orders.update_many({}, {"$pull": {"items": {"product_id": 1}}})
    return {"rows": [], "rows_affected": result.modified_count}


def mongo_d5(adapter) -> dict:
    products = list(adapter.database.products.find({"category.name": "Beauty"}, {"_id": 1}))
    product_ids = [product["_id"] for product in products]
    if not product_ids:
        return {"rows": [], "rows_affected": 0}
    affected = adapter.database.reviews.delete_many({"product_id": {"$in": product_ids}}).deleted_count
    affected += adapter.database.orders.update_many({}, {"$pull": {"items": {"product_id": {"$in": product_ids}}}}).modified_count
    affected += adapter.database.products.delete_many({"_id": {"$in": product_ids}}).deleted_count
    return {"rows": [], "rows_affected": affected}


def mongo_d6(adapter) -> dict:
    result = adapter.database.orders.update_many({"coupon": {"$exists": True}}, {"$unset": {"coupon": ""}})
    return {"rows": [], "rows_affected": result.modified_count}


def redis_d1(adapter) -> dict:
    deleted = adapter.client.delete("customer:1", "customer:1:addresses")
    return {"rows": [], "rows_affected": deleted}


def redis_d3(adapter) -> dict:
    review_ids = adapter.client.lrange("product:1:reviews", 0, -1)
    deleted = 0
    for review_id in review_ids:
        if adapter.client.hget(f"review:{review_id}", "rating") == "1":
            deleted += adapter.client.delete(f"review:{review_id}")
            adapter.client.lrem("product:1:reviews", 0, review_id)
    return {"rows": [], "rows_affected": deleted}


def redis_d4(adapter) -> dict:
    raw = adapter.client.get("order:1")
    if not raw:
        return {"rows": [], "rows_affected": 0}
    order = json.loads(raw)
    before = len(order.get("items", []))
    order["items"] = [item for item in order.get("items", []) if item.get("product_id") != 1]
    adapter.client.set("order:1", json.dumps(order))
    return {"rows": [], "rows_affected": before - len(order["items"])}


DELETE_SCENARIOS = {
    "d1": ScenarioDefinition("d1", "Delete customer with dependent records", {DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO, DatabaseTarget.REDIS}, {DatabaseTarget.MYSQL: sql_d1, DatabaseTarget.POSTGRES: sql_d1, DatabaseTarget.MONGO: mongo_d1, DatabaseTarget.REDIS: redis_d1}, mutating=True),
    "d2": ScenarioDefinition("d2", "Delete cancelled orders", {DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO}, {DatabaseTarget.MYSQL: sql_d2, DatabaseTarget.POSTGRES: sql_d2, DatabaseTarget.MONGO: mongo_d2}, mutating=True),
    "d3": ScenarioDefinition("d3", "Delete low rating reviews for product", {DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO, DatabaseTarget.REDIS}, {DatabaseTarget.MYSQL: sql_d3, DatabaseTarget.POSTGRES: sql_d3, DatabaseTarget.MONGO: mongo_d3, DatabaseTarget.REDIS: redis_d3}, mutating=True),
    "d4": ScenarioDefinition("d4", "Delete order item by product", {DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO, DatabaseTarget.REDIS}, {DatabaseTarget.MYSQL: sql_d4, DatabaseTarget.POSTGRES: sql_d4, DatabaseTarget.MONGO: mongo_d4, DatabaseTarget.REDIS: redis_d4}, mutating=True),
    "d5": ScenarioDefinition("d5", "Delete products in Beauty category", {DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO}, {DatabaseTarget.MYSQL: sql_d5, DatabaseTarget.POSTGRES: sql_d5, DatabaseTarget.MONGO: mongo_d5}, mutating=True),
    "d6": ScenarioDefinition("d6", "Delete coupons and unlink orders", {DatabaseTarget.MYSQL, DatabaseTarget.POSTGRES, DatabaseTarget.MONGO}, {DatabaseTarget.MYSQL: sql_d6, DatabaseTarget.POSTGRES: sql_d6, DatabaseTarget.MONGO: mongo_d6}, mutating=True),
}
