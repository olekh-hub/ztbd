
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE categories (id INT PRIMARY KEY, name VARCHAR(255));

CREATE TABLE suppliers (id INT PRIMARY KEY, name VARCHAR(255), country VARCHAR(255), phone VARCHAR(100));

CREATE TABLE products (
    id INT PRIMARY KEY,
    category_id INT,
    supplier_id INT,
    name VARCHAR(255),
    price DECIMAL(10,2),
    FOREIGN KEY (category_id) REFERENCES categories(id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
);

CREATE TABLE product_details (
    id INT PRIMARY KEY,
    product_id INT,
    specs TEXT,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE customers (
    id INT PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    registration_date DATETIME
);

CREATE TABLE addresses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    customer_id INT,
    street VARCHAR(255),
    city VARCHAR(255),
    postcode VARCHAR(20),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE coupons (id INT PRIMARY KEY, code VARCHAR(50), discount_pct INT);

CREATE TABLE orders (
    id INT PRIMARY KEY,
    customer_id INT,
    coupon_id INT,
    order_date DATE,
    status VARCHAR(50),
    total_price DECIMAL(12,2),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE order_items (
    id INT PRIMARY KEY,
    order_id INT,
    product_id INT,
    quantity INT,
    unit_price DECIMAL(10,2),
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

CREATE TABLE reviews (
    id INT PRIMARY KEY,
    product_id INT,
    customer_id INT,
    rating INT,
    comment TEXT,
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (customer_id) REFERENCES customers(id)
);

SET FOREIGN_KEY_CHECKS = 1;


