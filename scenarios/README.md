# Scenariusze testowe CRUD – ZTBD (ocena 5.0)

Folder zawiera **24 scenariusze testowe** (po 6 dla każdej operacji CRUD) wymagane na ocenę 5.0 zgodnie z regulaminem przedmiotu *Zaawansowane technologie baz danych*.

## Zakres projektu

- **Systemy relacyjne:** MySQL 8.0, PostgreSQL 15
- **Systemy nierelacyjne:** MongoDB (dokumentowy), Redis (klucz–wartość)
- **Schemat:** e-commerce, 10 tabel (`categories`, `suppliers`, `products`, `product_details`, `customers`, `addresses`, `coupons`, `orders`, `order_items`, `reviews`)
- **Rozmiary zbiorów danych** (zgodnie z wymogiem 4.0/5.0 – 500k / 1M / 10M):
  - **S (mały):** 500 000 rekordów w tabeli dominującej (np. `reviews`)
  - **M (średni):** 1 000 000 rekordów
  - **L (duży):** 10 000 000 rekordów (`orders`, `order_items`)
- **Próby:** 3 powtórzenia na scenariusz → **średnia czasu wykonania**
- **Warianty indeksowania:** każdy scenariusz uruchamiany dwukrotnie:
  - `NO_IDX` – tylko klucze główne (brak indeksów wtórnych)
  - `IDX` – z indeksami dedykowanymi pod dany scenariusz (B-tree/Hash/GIN/compound)
- **Analiza planów zapytań:** `EXPLAIN (ANALYZE, BUFFERS)` dla PG, `EXPLAIN ANALYZE` dla MySQL, `.explain("executionStats")` dla Mongo

## Hipoteza badawcza (wybrana)

**H1: Indeksy a wydajność** – zastosowanie indeksów znacząco poprawia wydajność operacji SELECT (R1–R6) kosztem spadku wydajności operacji INSERT i UPDATE (C1–C6, U1–U6). Weryfikacja przez porównanie średnich czasów `IDX` vs `NO_IDX` we wszystkich 24 scenariuszach.

## Elementy zaawansowane 5.0 (wybrane 2)

1. **Automatyzacja testów i generowania wyników** – skrypty Python (`pytest` + `pandas` + `matplotlib`) uruchamiające wszystkie 24 scenariusze × 4 bazy × 3 rozmiary × 3 próby × 2 warianty indeksowania.
2. **Wykorzystanie danych półustrukturalnych (JSON)** – pole `product_details.specs` oraz denormalizacja `orders→items` w MongoDB; porównanie czasu zapytań po polach JSON w PG (`jsonb`) vs MySQL (`JSON`) vs Mongo.

## Struktura pliku `scenarios.md`

Każdy scenariusz zawiera:
- **ID** (np. `C1`, `R3`, `U5`, `D2`)
- **Nazwę** i **opis biznesowy**
- **Zapytanie/operację** w pseudokodzie oraz w SQL/MongoDB/Redis
- **Indeksy** zakładane w wariancie `IDX`
- **Oczekiwany efekt** (hipoteza cząstkowa)
- **Metryki:** czas wykonania [ms], liczba I/O (jeśli dostępna), plan zapytania

Pełna lista scenariuszy: zobacz [`scenarios.md`](./scenarios.md).

## Macierz pokrycia

| Operacja | # scen. | Rozmiary | Bazy                         | Warianty |
|----------|--------:|----------|------------------------------|----------|
| CREATE   |    6    | S / M / L | MySQL, PG, Mongo, Redis     | NO_IDX / IDX |
| READ     |    6    | S / M / L | MySQL, PG, Mongo, Redis     | NO_IDX / IDX |
| UPDATE   |    6    | S / M / L | MySQL, PG, Mongo, Redis     | NO_IDX / IDX |
| DELETE   |    6    | S / M / L | MySQL, PG, Mongo, Redis     | NO_IDX / IDX |
| **Razem**| **24**  |           |                              |  |

Łączna liczba pomiarów: **24 × 4 bazy × 3 rozmiary × 3 próby × 2 warianty ≈ 1728 pomiarów**.
