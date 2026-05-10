db.customers.dropIndex("idx_customers_email");
db.customers.dropIndex("idx_customers_last_name");
db.customers.dropIndex("idx_customers_regdate");
db.customers.dropIndex("idx_customers_addresses_postcode");

db.products.dropIndex("idx_products_category_name");
db.products.dropIndex("idx_products_supplier_name");
db.products.dropIndex("idx_products_name");
db.products.dropIndex("idx_products_price");
db.products.dropIndex("idx_products_specs_warranty");

db.orders.dropIndex("idx_orders_customer");
db.orders.dropIndex("idx_orders_date");
db.orders.dropIndex("idx_orders_date_customer");
db.orders.dropIndex("idx_orders_status_date");
db.orders.dropIndex("idx_orders_coupon");
db.orders.dropIndex("idx_orders_items_product");
db.orders.dropIndex("idx_orders_id_items_product");

db.reviews.dropIndex("idx_reviews_product");
db.reviews.dropIndex("idx_reviews_customer");
db.reviews.dropIndex("idx_reviews_rating");
db.reviews.dropIndex("idx_reviews_product_rating");
db.reviews.dropIndex("idx_reviews_comment_text");
