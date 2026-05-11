# Scenariusze testowe CRUD – pełna specyfikacja

> Każdy scenariusz wykonywany w dwóch wariantach: **NO_IDX** (tylko PK) oraz **IDX** (z indeksami wtórnymi). 3 próby × 3 rozmiary zbioru (S/M/L) × 4 bazy danych.

---

## CREATE – 6 scenariuszy

### C1 – Masowy INSERT nowych klientów (batch)
**Opis:** Rejestracja 10 000 / 100 000 / 1 000 000 nowych klientów w jednej transakcji.
**Cel:** zmierzyć narzut utrzymania indeksów przy ładowaniu danych.
**SQL:**
```sql
INSERT INTO customers (id, first_name, last_name, email, registration_date)
VALUES (?, ?, ?, ?, ?);  -- wykonywane w batchu (executemany / COPY / LOAD DATA)
```
**Mongo:** `db.customers.insertMany([...])`
**Redis:** `HSET customer:{id} ...` w pipeline.
**Indeksy (IDX):** `UNIQUE(email)`, `INDEX(last_name)`, `INDEX(registration_date)`.
**Hipoteza:** `IDX` wolniejszy od `NO_IDX` o 15–40% ze względu na utrzymanie B-tree.

---

### C2 – INSERT zamówienia z pozycjami (transakcja wieloetapowa)
**Opis:** Wstawienie 1 zamówienia + 1–5 pozycji (`order_items`), powtórzone 10 000 razy.
**Cel:** sprawdzić koszt utrzymania FK i indeksów w transakcji OLTP.
**SQL:** `BEGIN; INSERT INTO orders ...; INSERT INTO order_items ... (wiele); COMMIT;`
**Mongo:** pojedynczy `insertOne` z zagnieżdżoną tablicą `items` (model zdenormalizowany).
**Indeksy (IDX):** `INDEX(customer_id)`, `INDEX(order_date)`, `INDEX(order_items.order_id)`, `INDEX(order_items.product_id)`.
**Hipoteza:** Mongo szybsze od RDBMS dzięki embedded docs; `IDX` w RDBMS spowolni zapis o 20–50%.

---

### C3 – Masowe dodawanie recenzji (append-heavy)
**Opis:** Wstawienie 500 000 nowych recenzji produktów (symulacja kampanii).
**Cel:** ocena kosztu indeksów przy workloadzie append-only.
**SQL:** `INSERT INTO reviews (product_id, customer_id, rating, comment) VALUES (...)` (batch 5 000).
**Mongo:** `db.reviews.insertMany([...])`.
**Redis:** `LPUSH product:{pid}:reviews {rid}` + `HSET review:{rid} ...`.
**Indeksy (IDX):** `INDEX(product_id)`, `INDEX(rating)`, `INDEX(customer_id)`.
**Hipoteza:** Redis najszybszy (in-memory); PostgreSQL z HOT updates lepszy od MySQL.

---

### C4 – INSERT produktów z FK do categories i suppliers
**Opis:** Wstawienie 100 000 nowych produktów z losowymi `category_id`, `supplier_id`.
**Cel:** wpływ sprawdzania kluczy obcych + indeksów FK na czas INSERT.
**SQL:** `INSERT INTO products (id, category_id, supplier_id, name, price) VALUES (...);`
**Mongo:** insert z zagnieżdżonymi (denormalizowanymi) obiektami `category` i `supplier`.
**Indeksy (IDX):** `INDEX(category_id)`, `INDEX(supplier_id)`, `INDEX(name)`, `INDEX(price)`.
**Hipoteza:** walidacja FK w PG/MySQL doda 5–15% kosztu; Mongo bez tej walidacji.

---

### C5 – INSERT adresów dla istniejących klientów (1:N)
**Opis:** Dla 200 000 klientów dodanie 1–3 nowych adresów (relacja jeden-do-wielu).
**Cel:** porównanie modelu relacyjnego (osobna tabela) vs dokumentowego (embedded array).
**SQL:** `INSERT INTO addresses (customer_id, street, city, postcode) VALUES (...)`.
**Mongo:** `db.customers.updateMany({_id:?}, {$push: {addresses: {...}}})`.
**Redis:** `SET customer:{id}:addresses <json>` (nadpisanie).
**Indeksy (IDX):** `INDEX(customer_id)`, `INDEX(postcode)`.
**Hipoteza:** Mongo `$push` wolniejszy niż czysty INSERT w RDBMS z powodu aktualizacji istniejącego dokumentu; Redis najszybszy.

---

### C6 – INSERT pozycji zamówień z kuponem (duża denormalizacja)
**Opis:** Wstawienie 1 000 000 `order_items` z jednoczesnym lookupem `coupon` i zapisem `unit_price` po rabacie.
**Cel:** ocenić koszt zapisu szerokiego wiersza oraz model zdenormalizowany w Mongo.
**SQL:** `INSERT INTO order_items ... SELECT ... FROM orders JOIN coupons ...`.
**Mongo:** aktualizacja dokumentu `orders` z `$push` do `items[]` i zapisanym zdenormalizowanym kuponem.
**Indeksy (IDX):** `INDEX(order_id)`, `INDEX(product_id)`, `INDEX(coupon_id)` w `orders`.
**Hipoteza:** Model zdenormalizowany Mongo zwiększa rozmiar dokumentu i spowalnia zapis przy dużych zamówieniach.

---

## READ – 6 scenariuszy

### R1 – Punktowe wyszukiwanie klienta po e-mailu
**Opis:** `SELECT * FROM customers WHERE email = ?` – losowo 1 000 różnych e-maili.
**Cel:** klasyczny test indeksu unikalnego vs full scan.
**SQL:** `SELECT * FROM customers WHERE email = ?;`
**Mongo:** `db.customers.find({email: ?})`.
**Redis:** brak bezpośredniej obsługi – wymaga indeksu wtórnego (`email:<x> → id`).
**Indeksy (IDX):** `UNIQUE INDEX(email)`.
**Hipoteza:** `IDX` > 1000× szybszy od `NO_IDX` na zbiorze L.

---

### R2 – Zapytanie zakresowe po dacie zamówienia
**Opis:** `SELECT id, customer_id, total_price FROM orders WHERE order_date BETWEEN ? AND ?` (7 dni).
**Cel:** test indeksu B-tree na kolumnie dat + sortowanie.
**SQL:** `SELECT ... WHERE order_date BETWEEN '2026-01-01' AND '2026-01-07' ORDER BY order_date;`
**Mongo:** `db.orders.find({order_date:{$gte:..,$lte:..}}).sort({order_date:1})`.
**Indeksy (IDX):** `INDEX(order_date)` oraz compound `(order_date, customer_id)`.
**Hipoteza:** compound index eliminujący sortowanie da największy zysk.

---

### R3 – JOIN wieloetapowy: TOP 10 klientów wg wydatków
**Opis:** Łączenie `customers → orders → order_items → products → categories`; agregacja `SUM(quantity*unit_price)`.
**Cel:** test planów zapytań i indeksów FK w złożonych JOIN-ach.
**SQL:**
```sql
SELECT c.id, c.last_name, SUM(oi.quantity * oi.unit_price) AS total
FROM customers c
JOIN orders o   ON o.customer_id = c.id
JOIN order_items oi ON oi.order_id = o.id
GROUP BY c.id, c.last_name
ORDER BY total DESC
LIMIT 10;
```
**Mongo:** `$lookup` + `$group` + `$sort` + `$limit` w agregacji.
**Indeksy (IDX):** `INDEX(orders.customer_id)`, `INDEX(order_items.order_id)`.
**Hipoteza:** PG z `hash join` i indeksami wygra z MySQL; Mongo (bez joinów natywnych) najwolniejszy.

---

### R4 – Agregacja: przychód per kategoria produktu
**Opis:** Suma sprzedaży pogrupowana po kategorii; 5 kategorii, dane z `order_items` + `products` + `categories`.
**Cel:** test zachowania przy pełnym skanie + agregacji (indeksy mają ograniczony zysk).
**SQL:**
```sql
SELECT cat.name, SUM(oi.quantity * oi.unit_price) AS revenue
FROM order_items oi
JOIN products p ON p.id = oi.product_id
JOIN categories cat ON cat.id = p.category_id
GROUP BY cat.name;
```
**Mongo:** `$lookup` + `$group` po `category.name` (zdenormalizowane).
**Indeksy (IDX):** `INDEX(products.category_id)`, covering index `(order_items.product_id, quantity, unit_price)`.
**Hipoteza:** Mongo z denormalizacją kategorii wygra dzięki braku lookupu.

---

### R5 – Wyszukiwanie pełnotekstowe w komentarzach recenzji
**Opis:** `SELECT * FROM reviews WHERE comment ILIKE '%excellent%'` na 1 000 000 opinii.
**Cel:** porównanie `LIKE %…%` (brak indeksu) vs indeksy full-text (GIN/InnoDB FULLTEXT/Mongo text).
**SQL PG (IDX):** `CREATE INDEX ON reviews USING gin (to_tsvector('english', comment));`
**MySQL (IDX):** `FULLTEXT(comment)` + `MATCH ... AGAINST`.
**Mongo (IDX):** `db.reviews.createIndex({comment: "text"})`.
**Hipoteza:** full-text index 50–500× szybszy od `ILIKE`; Mongo `$text` porównywalny z PG `to_tsvector`.

---

### R6 – Top-N produktów wg średniej oceny w kategorii
**Opis:** Dla kategorii "Electronics" – top 20 produktów o najwyższej średniej z `reviews.rating` (min. 100 recenzji).
**Cel:** złożone zapytanie z `GROUP BY`, `HAVING`, `ORDER BY`, `LIMIT`.
**SQL:**
```sql
SELECT p.id, p.name, AVG(r.rating) avg_r, COUNT(*) cnt
FROM products p
JOIN reviews r ON r.product_id = p.id
WHERE p.category_id = 1
GROUP BY p.id, p.name
HAVING COUNT(*) >= 100
ORDER BY avg_r DESC
LIMIT 20;
```
**Indeksy (IDX):** `INDEX(reviews.product_id, rating)`, `INDEX(products.category_id)`.
**Hipoteza:** covering index `(product_id, rating)` umożliwi *index-only scan* w PG → największy skok wydajności.

---

## UPDATE – 6 scenariuszy

### U1 – Punktowy UPDATE klienta po e-mailu
**Opis:** `UPDATE customers SET last_name = ? WHERE email = ?;` – 1 000 aktualizacji.
**Cel:** porównanie czasu lookupu wiersza z indeksem i bez.
**Mongo:** `db.customers.updateOne({email:?}, {$set:{last_name:?}})`.
**Redis:** `HSET customer:{id} last_name ?` (po odczycie z indeksu wtórnego).
**Indeksy (IDX):** `UNIQUE(email)`.
**Hipoteza:** `IDX` drastycznie szybszy przy odczycie, ale sam zapis podobny.

---

### U2 – Masowa zmiana statusu zamówień (batch UPDATE)
**Opis:** `UPDATE orders SET status='delivered' WHERE status='shipped' AND order_date < ?;` – ~500 000 wierszy.
**Cel:** ocena kosztu aktualizacji i narzutu utrzymania indeksu na kolumnie modyfikowanej.
**Indeksy (IDX):** `INDEX(status, order_date)` – efekt: szybszy zakres; ale też droższy update indeksu.
**Hipoteza:** `IDX` znacznie szybszy przy wyszukaniu, lekko wolniejszy przy samej modyfikacji.

---

### U3 – Zmiana ceny produktów w kategorii (UPDATE z JOIN)
**Opis:** Podniesienie cen o 10% dla wszystkich produktów z `category.name = 'Electronics'`.
**Cel:** update z warunkiem na FK – wpływ indeksu `category_id`.
**SQL:** `UPDATE products SET price = price * 1.10 WHERE category_id = 1;`
**Indeksy (IDX):** `INDEX(category_id)`.
**Hipoteza:** z indeksem ~5–20× szybsze wyszukanie targetów; update narzutu ok. 10%.

---

### U4 – UPDATE pola semi-structured (JSON/TEXT `specs`)
**Opis:** Aktualizacja konkretnego atrybutu w `product_details.specs` (np. `Warranty: 2 years` → `3 years`) dla 50 000 produktów.
**Cel:** porównanie modyfikacji JSON/JSONB vs TEXT; element zaawansowany – dane półustrukturalne.
**SQL PG:** `UPDATE product_details SET specs = jsonb_set(specs::jsonb, '{warranty}', '"3 years"');`
**MySQL:** `UPDATE product_details SET specs = JSON_REPLACE(specs, '$.warranty','3 years');`
**Mongo:** `db.products.updateMany({}, {$set:{"specs.warranty":"3 years"}})`.
**Indeksy (IDX):** PG: `CREATE INDEX ON product_details USING gin (specs jsonb_path_ops);` Mongo: indeks na `specs.warranty`.
**Hipoteza:** Mongo najwygodniejszy; PG `jsonb` z GIN konkurencyjny; MySQL najwolniejszy.

---

### U5 – Rekalkulacja `total_price` zamówienia po edycji `order_items`
**Opis:** Zmiana `quantity` w 10 000 losowych pozycji + aktualizacja sum w `orders`.
**Cel:** test propagacji zmian i kosztu utrzymania spójności danych.
**SQL:**
```sql
UPDATE order_items SET quantity = quantity + 1 WHERE id IN (...);
UPDATE orders o SET total_price = (
   SELECT SUM(oi.quantity * oi.unit_price) FROM order_items oi WHERE oi.order_id = o.id
) WHERE o.id IN (...);
```
**Mongo:** `$set` z użyciem `$map` i `$sum` w pipeline update (Mongo 4.2+).
**Indeksy (IDX):** `INDEX(order_items.order_id)`.
**Hipoteza:** Mongo (embedded items) wygra dzięki jednej operacji na dokumencie.

---

### U6 – Zmiana kuponów i kaskadowy wpływ na zamówienia
**Opis:** Aktualizacja `discount_pct` w 50 kuponach; ponowne przeliczenie cen w 200 000 powiązanych zamówień.
**Cel:** ocena wpływu indeksów FK `coupon_id` na propagację aktualizacji.
**Indeksy (IDX):** `INDEX(orders.coupon_id)`.
**Hipoteza:** bez indeksu `coupon_id` kaskadowy update ~O(N²) dla wielu kuponów.

---

## DELETE – 6 scenariuszy

### D1 – Usunięcie klienta z kaskadą (adresy + recenzje)
**Opis:** `DELETE FROM customers WHERE id = ?` z `ON DELETE CASCADE` dla `addresses` i `reviews` – 1 000 klientów.
**Cel:** wpływ indeksów FK na czas kaskady.
**Indeksy (IDX):** `INDEX(addresses.customer_id)`, `INDEX(reviews.customer_id)`.
**Hipoteza:** bez indeksów na FK kaskadowe delete to pełny skan → kwadratowy narzut.

---

### D2 – Masowe DELETE starych anulowanych zamówień
**Opis:** `DELETE FROM orders WHERE status='cancelled' AND order_date < NOW() - INTERVAL 1 YEAR;` – ~800 000 wierszy.
**Cel:** ocena kosztu dużego DELETE z warunkiem złożonym.
**Indeksy (IDX):** `INDEX(status, order_date)`.
**Hipoteza:** z indeksem compound ~10× szybszy; w PG dodatkowo `VACUUM` obciążony.

---

### D3 – Usunięcie recenzji z niską oceną dla produktu
**Opis:** `DELETE FROM reviews WHERE product_id = ? AND rating = 1;` – wykonywane dla 100 różnych produktów.
**Cel:** selektywny DELETE – wpływ indeksu compound.
**Mongo:** `db.reviews.deleteMany({product_id:?, rating:1})`.
**Indeksy (IDX):** `INDEX(product_id, rating)`.
**Hipoteza:** compound daje *index-only* filtrowanie; bez indeksu – pełny skan 1M recenzji.

---

### D4 – DELETE konkretnej pozycji zamówienia
**Opis:** `DELETE FROM order_items WHERE order_id = ? AND product_id = ?;` – 10 000 powtórzeń.
**Cel:** punktowy DELETE z indeksem compound na FK.
**Mongo:** `db.orders.updateOne({_id:?}, {$pull:{items:{product_id:?}}})`.
**Indeksy (IDX):** `INDEX(order_id, product_id)`.
**Hipoteza:** Mongo `$pull` wolniejszy niż DELETE w RDBMS, bo przepisuje dokument.

---

### D5 – Masowe usunięcie produktów z kategorii (z kaskadą `product_details`)
**Opis:** Usunięcie wszystkich produktów z kategorii "Beauty" (~80 rekordów, ale z kaskadą do `product_details`, `order_items`, `reviews`).
**Cel:** ocena kaskadowych DELETE i potrzeby indeksów na wszystkich FK.
**Indeksy (IDX):** `INDEX(product_details.product_id)`, `INDEX(order_items.product_id)`, `INDEX(reviews.product_id)`.
**Hipoteza:** bez indeksów FK kaskada paraliżuje bazę; z indeksami w PG poniżej 1 s.

---

### D6 – DELETE wygasłych kuponów + rozłączenie zamówień
**Opis:** Usunięcie 20 kuponów + `UPDATE orders SET coupon_id = NULL WHERE coupon_id IN (...)` jako zamiennik kaskady.
**Cel:** scenariusz "miękkiej kaskady" – test czasu wyszukania zamówień do rozłączenia.
**Indeksy (IDX):** `INDEX(orders.coupon_id)`.
**Hipoteza:** indeks na `coupon_id` przyspiesza etap UPDATE 50–100×.

---

## Mapowanie scenariuszy na bazy danych

| ID  | MySQL | PostgreSQL | MongoDB | Redis | Uwagi                                     |
|-----|:-----:|:----------:|:-------:|:-----:|-------------------------------------------|
| C1  | ✅    | ✅         | ✅      | ✅    | Redis w pipeline                          |
| C2  | ✅    | ✅         | ✅      | ⚠️    | Redis – brak natywnych transakcji         |
| C3  | ✅    | ✅         | ✅      | ✅    |                                           |
| C4  | ✅    | ✅         | ✅      | ✅    |                                           |
| C5  | ✅    | ✅         | ✅      | ✅    | Mongo: `$push`; Redis: SET JSON           |
| C6  | ✅    | ✅         | ✅      | ⚠️    |                                           |
| R1  | ✅    | ✅         | ✅      | ⚠️    | Redis – wymaga indeksu wtórnego           |
| R2  | ✅    | ✅         | ✅      | ❌    | Zakres czasowy – Redis nieodpowiedni      |
| R3  | ✅    | ✅         | ✅      | ❌    | Mongo `$lookup`                           |
| R4  | ✅    | ✅         | ✅      | ❌    |                                           |
| R5  | ✅    | ✅         | ✅      | ❌    | Full-text                                 |
| R6  | ✅    | ✅         | ✅      | ❌    |                                           |
| U1  | ✅    | ✅         | ✅      | ✅    |                                           |
| U2  | ✅    | ✅         | ✅      | ❌    |                                           |
| U3  | ✅    | ✅         | ✅      | ❌    |                                           |
| U4  | ✅    | ✅         | ✅      | ⚠️    | JSON semi-structured                      |
| U5  | ✅    | ✅         | ✅      | ❌    |                                           |
| U6  | ✅    | ✅         | ✅      | ❌    |                                           |
| D1  | ✅    | ✅         | ✅      | ✅    |                                           |
| D2  | ✅    | ✅         | ✅      | ❌    |                                           |
| D3  | ✅    | ✅         | ✅      | ✅    |                                           |
| D4  | ✅    | ✅         | ✅      | ⚠️    | Mongo `$pull`                             |
| D5  | ✅    | ✅         | ✅      | ❌    |                                           |
| D6  | ✅    | ✅         | ✅      | ❌    |                                           |

Legenda: ✅ pełna obsługa · ⚠️ obsługa z zastrzeżeniami (obejście) · ❌ nieadekwatne.

---

## Zestaw indeksów wtórnych (wariant IDX)

```sql
-- customers
CREATE UNIQUE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_last_name ON customers(last_name);
CREATE INDEX idx_customers_regdate ON customers(registration_date);

-- addresses
CREATE INDEX idx_addresses_customer ON addresses(customer_id);
CREATE INDEX idx_addresses_postcode ON addresses(postcode);

-- products
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_supplier ON products(supplier_id);
CREATE INDEX idx_products_price ON products(price);

-- product_details
CREATE INDEX idx_pd_product ON product_details(product_id);
-- PG: CREATE INDEX idx_pd_specs_gin ON product_details USING gin (specs::jsonb);

-- orders
CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_orders_status_date ON orders(status, order_date);
CREATE INDEX idx_orders_coupon ON orders(coupon_id);

-- order_items
CREATE INDEX idx_oi_order ON order_items(order_id);
CREATE INDEX idx_oi_product ON order_items(product_id);
CREATE INDEX idx_oi_order_product ON order_items(order_id, product_id);

-- reviews
CREATE INDEX idx_reviews_product ON reviews(product_id);
CREATE INDEX idx_reviews_customer ON reviews(customer_id);
CREATE INDEX idx_reviews_product_rating ON reviews(product_id, rating);
-- PG: CREATE INDEX idx_reviews_comment_fts ON reviews USING gin (to_tsvector('english', comment));
-- MySQL: CREATE FULLTEXT INDEX idx_reviews_comment_ft ON reviews(comment);
```

MongoDB – analogicznie przez `db.<col>.createIndex({...})` (m.in. compound, text, `jsonb`-like na embedded).

---

## Metodyka pomiaru

1. **Rozgrzewka (warm-up):** 1 uruchomienie przed pomiarem, by wypełnić bufory (`shared_buffers`, `InnoDB buffer pool`, `WiredTiger cache`).
2. **Czyszczenie cache** między seriami (`SYSTEM FLUSH` / `RESET QUERY CACHE` / restart container) – opcjonalnie, aby pokazać cold/warm start.
3. **Mierzenie:** `time.perf_counter()` w Pythonie wokół pojedynczej operacji/transakcji; dla SQL także `EXPLAIN ANALYZE`.
4. **Wynik:** średnia arytmetyczna z 3 prób + odchylenie standardowe.
5. **Wizualizacja:** `matplotlib` – słupki grupowane per (operacja × rozmiar × baza × {NO_IDX, IDX}).

---

## Następne kroki

1. Dodać katalog `benchmarks/` ze skryptami Pythonowymi uruchamiającymi wszystkie 24 scenariusze.
2. Dodać plik `indexes.sql` (IDX) i `indexes_drop.sql` (NO_IDX) do przełączania wariantów.
3. Wygenerować trzy zestawy danych (S/M/L) przez `uv run ztbd generate`.
4. Przygotować raport + prezentację z wnioskami dot. H1 (indeksy a wydajność).
