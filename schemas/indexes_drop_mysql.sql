DROP INDEX idx_reviews_comment_ft ON reviews;
DROP INDEX idx_reviews_product_rating ON reviews;
DROP INDEX idx_reviews_rating ON reviews;
DROP INDEX idx_reviews_customer ON reviews;
DROP INDEX idx_reviews_product ON reviews;

DROP INDEX idx_oi_product_covering ON order_items;
DROP INDEX idx_oi_order_product ON order_items;
DROP INDEX idx_oi_product ON order_items;
DROP INDEX idx_oi_order ON order_items;

DROP INDEX idx_orders_coupon ON orders;
DROP INDEX idx_orders_status_date ON orders;
DROP INDEX idx_orders_date_customer ON orders;
DROP INDEX idx_orders_date ON orders;
DROP INDEX idx_orders_customer ON orders;

DROP INDEX idx_pd_specs_warranty ON product_details;
DROP INDEX idx_pd_product ON product_details;

DROP INDEX idx_products_price ON products;
DROP INDEX idx_products_name ON products;
DROP INDEX idx_products_supplier ON products;
DROP INDEX idx_products_category ON products;

DROP INDEX idx_addresses_postcode ON addresses;
DROP INDEX idx_addresses_customer ON addresses;

DROP INDEX idx_customers_regdate ON customers;
DROP INDEX idx_customers_last_name ON customers;
DROP INDEX idx_customers_email ON customers;
