-- 1. Kategorie
CREATE TABLE categories (id INT PRIMARY KEY, name TEXT);

-- 2. Dostawcy
CREATE TABLE suppliers (id INT PRIMARY KEY, name TEXT, country TEXT, phone TEXT);

-- 3. Produkty
CREATE TABLE products (
    id INT PRIMARY KEY,
    category_id INT REFERENCES categories(id),
    supplier_id INT REFERENCES suppliers(id),
    name TEXT,
    price DECIMAL(10,2)
);

-- 4. Detale produktów
CREATE TABLE product_details (
    id INT PRIMARY KEY,
    product_id INT REFERENCES products(id),
    specs TEXT
);

-- 5. Klienci
CREATE TABLE customers (
    id INT PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    registration_date TIMESTAMP
);

-- 6. Adresy
CREATE TABLE addresses (
    id SERIAL PRIMARY KEY, -- Tu dajemy SERIAL, bo w generatorze adresy nie mają własnego ID
    customer_id INT REFERENCES customers(id),
    street TEXT,
    city TEXT,
    postcode TEXT
);

-- 7. Kupony
CREATE TABLE coupons (id INT PRIMARY KEY, code TEXT, discount_pct INT);

-- 8. Zamówienia
CREATE TABLE orders (
    id INT PRIMARY KEY,
    customer_id INT REFERENCES customers(id),
    coupon_id INT, -- Bez REFERENCES, bo kupon może być pusty
    order_date DATE,
    status TEXT,
    total_price DECIMAL(12,2)
);

-- 9. Pozycje zamówienia
CREATE TABLE order_items (
    id INT PRIMARY KEY,
    order_id INT REFERENCES orders(id),
    product_id INT REFERENCES products(id),
    quantity INT,
    unit_price DECIMAL(10,2)
);

-- 10. Opinie
CREATE TABLE reviews (
    id INT PRIMARY KEY,
    product_id INT REFERENCES products(id),
    customer_id INT REFERENCES customers(id),
    rating INT,
    comment TEXT
);