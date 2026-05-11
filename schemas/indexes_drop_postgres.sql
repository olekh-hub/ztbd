DROP INDEX IF EXISTS idx_pd_specs_gin;
DROP INDEX IF EXISTS idx_reviews_comment_fts;
DROP INDEX IF EXISTS idx_reviews_product_rating;
DROP INDEX IF EXISTS idx_reviews_rating;
DROP INDEX IF EXISTS idx_reviews_customer;
DROP INDEX IF EXISTS idx_reviews_product;

DROP INDEX IF EXISTS idx_oi_product_covering;
DROP INDEX IF EXISTS idx_oi_order_product;
DROP INDEX IF EXISTS idx_oi_product;
DROP INDEX IF EXISTS idx_oi_order;

DROP INDEX IF EXISTS idx_orders_coupon;
DROP INDEX IF EXISTS idx_orders_status_date;
DROP INDEX IF EXISTS idx_orders_date_customer;
DROP INDEX IF EXISTS idx_orders_date;
DROP INDEX IF EXISTS idx_orders_customer;

DROP INDEX IF EXISTS idx_pd_product;

DROP INDEX IF EXISTS idx_products_price;
DROP INDEX IF EXISTS idx_products_name;
DROP INDEX IF EXISTS idx_products_supplier;
DROP INDEX IF EXISTS idx_products_category;

DROP INDEX IF EXISTS idx_addresses_postcode;
DROP INDEX IF EXISTS idx_addresses_customer;

DROP INDEX IF EXISTS idx_customers_regdate;
DROP INDEX IF EXISTS idx_customers_last_name;
DROP INDEX IF EXISTS idx_customers_email;
