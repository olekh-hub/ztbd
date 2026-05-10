import pandas as pd

from ztbd.ingestion.transforms import build_customers, build_products, build_reviews


def test_build_customers_embeds_addresses() -> None:
    frames = {
        "customers": pd.DataFrame(
            [{"id": 1, "first_name": "Ada", "last_name": "Lovelace", "email": "ada@example.com", "registration_date": "2024-01-01"}]
        ),
        "addresses": pd.DataFrame([{"customer_id": 1, "street": "Main", "city": "London", "postcode": "123"}]),
    }

    customers = build_customers(frames)

    assert customers == [
        {
            "_id": 1,
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@example.com",
            "registration_date": "2024-01-01",
            "addresses": [{"street": "Main", "city": "London", "postcode": "123"}],
        }
    ]


def test_build_products_denormalizes_category_supplier_and_specs() -> None:
    frames = {
        "products": pd.DataFrame([{"id": 10, "category_id": 1, "supplier_id": 2, "name": "Laptop", "price": 99.0}]),
        "categories": pd.DataFrame([{"id": 1, "name": "Electronics"}]),
        "suppliers": pd.DataFrame([{"id": 2, "name": "Acme", "country": "PL", "phone": "123"}]),
        "product_details": pd.DataFrame([{"id": 10, "product_id": 10, "specs": '{"warranty":"2 years"}'}]),
    }

    products = build_products(frames)

    assert products[0]["_id"] == 10
    assert products[0]["category"]["name"] == "Electronics"
    assert products[0]["supplier"]["name"] == "Acme"
    assert products[0]["specs"] == {"warranty": "2 years"}


def test_build_reviews_uses_mongo_id() -> None:
    reviews = build_reviews(
        {
            "reviews": pd.DataFrame(
                [{"id": 5, "product_id": 10, "customer_id": 1, "rating": 4, "comment": "nice"}]
            )
        }
    )

    assert reviews == [{"_id": 5, "product_id": 10, "customer_id": 1, "rating": 4, "comment": "nice"}]
