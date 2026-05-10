import random
import json
import csv

from faker import Faker

from ztbd.config import SIZE_PROFILES
from ztbd.csv_store import CsvStore
from ztbd.generation import DataGenerator


def test_generator_writes_test_profile_contract(tmp_path) -> None:
    fake = Faker("en_US")
    fake.seed_instance(123)
    generator = DataGenerator(
        profile=SIZE_PROFILES["test"],
        store=CsvStore(tmp_path),
        faker=fake,
        rng=random.Random(123),
    )

    generator.generate()

    customers = (tmp_path / "customers.csv").read_text(encoding="utf-8").splitlines()
    addresses = (tmp_path / "addresses.csv").read_text(encoding="utf-8").splitlines()
    orders = (tmp_path / "orders.csv").read_text(encoding="utf-8").splitlines()
    reviews = (tmp_path / "reviews.csv").read_text(encoding="utf-8").splitlines()
    with (tmp_path / "product_details.csv").open(newline="", encoding="utf-8") as file:
        product_details = list(csv.DictReader(file))

    assert customers[0] == "id,first_name,last_name,email,registration_date"
    assert addresses[0] == "customer_id,street,city,postcode"
    assert json.loads(product_details[0]["specs"])["warranty"] == "2 years"
    assert len(customers) == SIZE_PROFILES["test"].customers + 1
    assert len(orders) == SIZE_PROFILES["test"].orders + 1
    assert len(reviews) == SIZE_PROFILES["test"].reviews + 1
