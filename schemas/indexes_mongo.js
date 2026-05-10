db.customers.createIndex({ email: 1 }, { unique: true, name: "idx_customers_email" });
db.customers.createIndex({ last_name: 1 }, { name: "idx_customers_last_name" });
db.customers.createIndex({ registration_date: 1 }, { name: "idx_customers_regdate" });
db.customers.createIndex({ "addresses.postcode": 1 }, { name: "idx_customers_addresses_postcode" });

db.products.createIndex({ "category.name": 1 }, { name: "idx_products_category_name" });
db.products.createIndex({ "supplier.name": 1 }, { name: "idx_products_supplier_name" });
db.products.createIndex({ name: 1 }, { name: "idx_products_name" });
db.products.createIndex({ price: 1 }, { name: "idx_products_price" });
db.products.createIndex({ "specs.warranty": 1 }, { name: "idx_products_specs_warranty" });

db.orders.createIndex({ customer_id: 1 }, { name: "idx_orders_customer" });
db.orders.createIndex({ order_date: 1 }, { name: "idx_orders_date" });
db.orders.createIndex({ order_date: 1, customer_id: 1 }, { name: "idx_orders_date_customer" });
db.orders.createIndex({ status: 1, order_date: 1 }, { name: "idx_orders_status_date" });
db.orders.createIndex({ "coupon.id": 1 }, { name: "idx_orders_coupon" });
db.orders.createIndex({ "items.product_id": 1 }, { name: "idx_orders_items_product" });
db.orders.createIndex({ _id: 1, "items.product_id": 1 }, { name: "idx_orders_id_items_product" });

db.reviews.createIndex({ product_id: 1 }, { name: "idx_reviews_product" });
db.reviews.createIndex({ customer_id: 1 }, { name: "idx_reviews_customer" });
db.reviews.createIndex({ rating: 1 }, { name: "idx_reviews_rating" });
db.reviews.createIndex({ product_id: 1, rating: 1 }, { name: "idx_reviews_product_rating" });
db.reviews.createIndex({ comment: "text" }, { name: "idx_reviews_comment_text" });
