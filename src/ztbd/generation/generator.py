import json
import random
from collections.abc import Iterable

from faker import Faker

from ztbd.config import DataSizeProfile
from ztbd.csv_store import CsvStore


MARKET_DATA = {
    "Electronics": ["Smartphone", "Laptop", "Tablet", "Smartwatch", "Headphones"],
    "Home": ["Coffee Maker", "Vacuum", "Desk Lamp", "Sofa", "Air Purifier"],
    "Fashion": ["T-Shirt", "Jeans", "Sneakers", "Winter Jacket", "Leather Belt"],
    "Sport": ["Yoga Mat", "Dumbbells", "Bicycle", "Tent", "Running Shoes"],
    "Beauty": ["Perfume", "Face Cream", "Hair Dryer", "Lipstick", "Mascara"],
}


class DataGenerator:
    def __init__(
        self,
        profile: DataSizeProfile,
        store: CsvStore,
        faker: Faker | None = None,
        rng: random.Random | None = None,
    ):
        self.profile = profile
        self.store = store
        self.fake = faker or Faker("en_US")
        self.rng = rng or random.Random()

    def generate(self) -> None:
        self.store.ensure_dir()
        categories = list(MARKET_DATA.keys())
        supplier_ids = list(range(1, 21))
        product_ids = list(self._product_ids(categories))
        coupon_ids = list(range(1, 51))

        self.store.write_rows("categories", self._categories(categories))
        self.store.write_rows("suppliers", self._suppliers(supplier_ids))
        self.store.write_rows("products", self._products(categories, supplier_ids))
        self.store.write_rows("product_details", self._product_details(categories))
        self.store.write_rows("customers", self._customers())
        self.store.write_rows("addresses", self._addresses())
        self.store.write_rows("coupons", self._coupons(coupon_ids))
        self._write_orders_and_items(product_ids, coupon_ids)
        self.store.write_rows("reviews", self._reviews(product_ids))

    def _categories(self, categories: list[str]) -> Iterable[list[object]]:
        for category_id, name in enumerate(categories, 1):
            yield [category_id, name]

    def _suppliers(self, supplier_ids: list[int]) -> Iterable[list[object]]:
        for supplier_id in supplier_ids:
            yield [supplier_id, self.fake.company(), self.fake.country(), self.fake.phone_number()]

    def _product_ids(self, categories: list[str]) -> Iterable[int]:
        product_id = 1
        for category in categories:
            for _item in MARKET_DATA[category]:
                for _brand in ["A-Tech", "Premium", "ValueMax", "EcoLine"]:
                    yield product_id
                    product_id += 1

    def _products(self, categories: list[str], supplier_ids: list[int]) -> Iterable[list[object]]:
        product_id = 1
        for category_id, category in enumerate(categories, 1):
            for item in MARKET_DATA[category]:
                for brand in ["A-Tech", "Premium", "ValueMax", "EcoLine"]:
                    price = round(self.rng.uniform(20.0, 3000.0), 2)
                    yield [product_id, category_id, self.rng.choice(supplier_ids), f"{brand} {item}", price]
                    product_id += 1

    def _product_details(self, categories: list[str]) -> Iterable[list[object]]:
        for product_id in self._product_ids(categories):
            specs = json.dumps(
                {
                    "color": self.fake.color_name(),
                    "material": self.fake.word(),
                    "warranty": "2 years",
                }
            )
            yield [product_id, product_id, specs]

    def _customers(self) -> Iterable[list[object]]:
        for customer_id in range(1, self.profile.customers + 1):
            first_name = self.fake.first_name()
            last_name = self.fake.last_name()
            email = f"{first_name}{last_name}{customer_id}@example.com"
            registration_date = self.fake.date_between(start_date="-5y", end_date="-1y")
            yield [customer_id, first_name, last_name, email, registration_date]

    def _addresses(self) -> Iterable[list[object]]:
        for customer_id in range(1, self.profile.customers + 1):
            for _ in range(self.rng.randint(1, 2)):
                yield [
                    customer_id,
                    self.fake.street_address().replace(",", ""),
                    self.fake.city(),
                    self.fake.postcode(),
                ]

    def _coupons(self, coupon_ids: list[int]) -> Iterable[list[object]]:
        for coupon_id in coupon_ids:
            yield [coupon_id, f"SAVE{self.rng.randint(10, 50)}", self.rng.randint(5, 25)]

    def _write_orders_and_items(self, product_ids: list[int], coupon_ids: list[int]) -> None:
        item_id = 1
        status_options = ["delivered", "shipped", "paid", "cancelled"]

        with self.store.path_for("orders").open("w", newline="", encoding="utf-8") as orders_file:
            with self.store.path_for("order_items").open("w", newline="", encoding="utf-8") as items_file:
                import csv

                order_writer = csv.writer(orders_file)
                item_writer = csv.writer(items_file)
                order_writer.writerow(["id", "customer_id", "coupon_id", "order_date", "status", "total_price"])
                item_writer.writerow(["id", "order_id", "product_id", "quantity", "unit_price"])

                for order_id in range(1, self.profile.orders + 1):
                    customer_id = self.rng.randint(1, self.profile.customers)
                    coupon = self.rng.choice(coupon_ids) if self.rng.random() < 0.2 else ""
                    order_date = self.fake.date_this_year()
                    status = self.rng.choice(status_options)
                    total_price = 0

                    for _ in range(self.rng.randint(1, 4)):
                        product_id = self.rng.choice(product_ids)
                        quantity = self.rng.randint(1, 3)
                        unit_price = round(self.rng.uniform(20.0, 2500.0), 2)
                        item_writer.writerow([item_id, order_id, product_id, quantity, unit_price])
                        total_price += quantity * unit_price
                        item_id += 1

                    order_writer.writerow([order_id, customer_id, coupon, order_date, status, round(total_price, 2)])

    def _reviews(self, product_ids: list[int]) -> Iterable[list[object]]:
        for review_id in range(1, self.profile.reviews + 1):
            yield [
                review_id,
                self.rng.choice(product_ids),
                self.rng.randint(1, self.profile.customers),
                self.rng.randint(1, 5),
                self.fake.sentence(),
            ]
