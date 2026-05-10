from collections import defaultdict
import json
from typing import Any, Iterator, cast

import pandas as pd

from ztbd.csv_store import CsvStore


STATIC_FRAME_TABLES = [
    "addresses",
    "categories",
    "coupons",
    "customers",
    "product_details",
    "products",
    "reviews",
    "suppliers",
]


Document = dict[str, Any]


def records(frame: pd.DataFrame) -> list[Document]:
    return cast(list[Document], frame.to_dict("records"))


def clean_document(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: clean_document(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean_document(item) for item in value]
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def parse_json_value(value: Any) -> Any:
    value = clean_document(value)
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def read_static_frames(store: CsvStore) -> dict[str, pd.DataFrame]:
    return {table: store.read_frame(table) for table in STATIC_FRAME_TABLES}


def build_customers(frames: dict[str, pd.DataFrame]) -> list[Document]:
    addresses_grouped: defaultdict[int, list[Document]] = defaultdict(list)
    for address in records(frames["addresses"]):
        customer_id = int(address.pop("customer_id"))
        addresses_grouped[customer_id].append(clean_document(address))

    customers: list[Document] = []
    for row in records(frames["customers"]):
        customer = cast(Document, clean_document(row))
        customer["_id"] = int(customer.pop("id"))
        customer["addresses"] = clean_document(addresses_grouped.get(customer["_id"], []))
        customers.append(customer)
    return customers


def build_products(frames: dict[str, pd.DataFrame]) -> list[Document]:
    categories = cast(dict[Any, Document], frames["categories"].set_index("id").to_dict("index"))
    suppliers = cast(dict[Any, Document], frames["suppliers"].set_index("id").to_dict("index"))
    details = cast(dict[Any, Document], frames["product_details"].set_index("id").to_dict("index"))

    products: list[Document] = []
    for row in records(frames["products"]):
        product = cast(Document, clean_document(row))
        product["_id"] = int(product.pop("id"))
        product["category"] = clean_document(categories.get(product.pop("category_id"), {}))
        product["supplier"] = clean_document(suppliers.get(product.pop("supplier_id"), {}))
        product["specs"] = parse_json_value(details.get(product["_id"], {}).get("specs", ""))
        products.append(product)
    return products


def build_reviews(frames: dict[str, pd.DataFrame]) -> list[Document]:
    reviews: list[Document] = []
    for row in records(frames["reviews"]):
        review = cast(Document, clean_document(row))
        review["_id"] = int(review.pop("id"))
        reviews.append(review)
    return reviews


def build_order_items(store: CsvStore) -> dict[int, list[Document]]:
    items: defaultdict[int, list[Document]] = defaultdict(list)
    for chunk in pd.read_csv(store.path_for("order_items"), chunksize=100_000):
        for row in records(chunk):
            order_id = int(row.pop("order_id"))
            items[order_id].append(clean_document(row))
    return items


def iter_orders(store: CsvStore, frames: dict[str, pd.DataFrame], order_batch_size: int) -> Iterator[list[Document]]:
    order_items = build_order_items(store)
    coupons = cast(dict[Any, Document], frames["coupons"].set_index("id").to_dict("index"))

    for chunk in pd.read_csv(store.path_for("orders"), chunksize=order_batch_size):
        orders: list[Document] = []
        for row in records(chunk):
            order = cast(Document, clean_document(row))
            order["_id"] = int(order.pop("id"))
            order["items"] = order_items.get(order["_id"], [])
            coupon_id = order.pop("coupon_id", None)
            if coupon_id is not None:
                order["coupon"] = clean_document(coupons.get(coupon_id, {}))
            orders.append(order)
        yield orders
