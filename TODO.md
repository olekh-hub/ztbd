# Plan pracy – ZTBD projekt na ocenę 5.0

> Dokument prezentuje kompletną listę zadań niezbędnych do uzyskania oceny **5.0** z projektu *Zaawansowane technologie baz danych* (e-commerce, 4 SZBD). Zadania pogrupowane są według poziomu wymagań z regulaminu.

---

## Spis treści

1. [Status projektu](#status-projektu)
2. [Poziom 3.0 – podstawa teoretyczna](#poziom-30--podstawa-teoretyczna)
3. [Poziom 4.0 – rozszerzenia techniczne](#poziom-40--rozszerzenia-techniczne)
4. [Poziom 5.0 – elementy zaawansowane](#poziom-50--elementy-zaawansowane)
5. [Hipoteza badawcza](#hipoteza-badawcza)
6. [Produkty końcowe](#produkty-końcowe)
7. [Harmonogram i kolejność prac](#harmonogram-i-kolejność-prac)
8. [Podział zadań w zespole](#podział-zadań-w-zespole)

---

## Status projektu

### ✅ Zrobione

| Element | Plik / Miejsce | Status |
|---|---|:---:|
| 4 SZBD w Dockerze (MySQL, PostgreSQL, MongoDB, Redis) | `docker-compose.yml` | ✅ |
| 10 tabel w modelu relacyjnym | `schemas/mysql_schema.sql`, `schemas/postgre_schema.sql` | ✅ |
| Generator danych (rozmiar L) | `uv run ztbd generate` | ✅ |
| Import do 4 baz | `uv run ztbd ingest` | ✅ |
| 24 scenariusze CRUD (6 × operacja) | `scenarios/scenarios.md` | ✅ |
| 2+ różne modele danych (relacyjny, dokumentowy, klucz–wartość) | MongoDB + Redis | ✅ |

### 🔄 Do zrobienia

Wszystko poniżej w sekcjach 3.0 → 4.0 → 5.0.

---

## Poziom 3.0 – podstawa teoretyczna

> Materiały trafią do sprawozdania pisemnego oraz prezentacji. To **największa** pozostała część pracy tekstowej.

### 📝 Sprawozdanie – sekcje teoretyczne

- [ ] **Cel i zakres pracy** (~1 strona) – jasno określony temat i zakres analiz
- [ ] **Opis wybranych SZBD** (~4–6 stron)
  - [ ] MySQL 8.0 – architektura, silnik InnoDB, model relacyjny
  - [ ] PostgreSQL 15 – MVCC, typy zaawansowane (JSONB, GIN)
  - [ ] MongoDB – model dokumentowy, WiredTiger, replica sets
  - [ ] Redis – model klucz–wartość, struktury danych, persistence (RDB/AOF)
- [ ] **Zalety i wady każdego SZBD** (tabela porównawcza)
- [ ] **Charakterystyki teoretyczne** (per silnik)
  - [ ] Awaryjność (HA, replikacja, failover)
  - [ ] Bezpieczeństwo (role, szyfrowanie, TLS)
  - [ ] Migracje (narzędzia, strategie)
  - [ ] Integracje (sterowniki, ORM/ODM)
  - [ ] Skalowalność (wertykalna vs horyzontalna, sharding)
- [ ] **Obszary biznesowych zastosowań** – kiedy wybrać jaki silnik (use-case matrix)
- [ ] **Opis zbioru danych**
  - [ ] Diagram ERD (10 tabel) – np. w dbdiagram.io / Mermaid
  - [ ] Opis każdej tabeli + relacji
  - [ ] Parametry wolumenowe (liczba rekordów per rozmiar)
- [ ] **Opis aplikacji testowej**
  - [ ] Zdefiniowanie wymagań funkcjonalnych i niefunkcjonalnych
  - [ ] Wykorzystane technologie i narzędzia (Python, Docker, Faker, pandas, matplotlib)
  - [ ] Opis działania aplikacji (flow: generate → import → benchmark → report)

---

## Poziom 4.0 – rozszerzenia techniczne

### 🧪 Dane testowe w 3 rozmiarach

- [x] **Sparametryzować generator danych** – argumenty `--size S|M|L` oraz `--out-dir`
  - [ ] S = 500 000 rekordów w tabeli dominującej (`orders` / `reviews`)
  - [ ] M = 1 000 000 rekordów
  - [ ] L = 10 000 000 rekordów (obecny stan)
- [ ] Osobne katalogi: `data/s/`, `data/m/`, `data/l/`
- [ ] Udokumentować liczbę rekordów w każdej tabeli per rozmiar

### 🔑 Indeksowanie

- [ ] **Plik `indexes.sql`** – wszystkie indeksy wtórne dla MySQL + PostgreSQL (zestaw w `scenarios/scenarios.md`)
- [ ] **Plik `indexes_drop.sql`** – `DROP INDEX` dla wariantu `NO_IDX`
- [ ] **Plik `indexes_mongo.js`** – `db.*.createIndex(...)` dla Mongo
- [ ] **Plik `indexes_redis.md`** – opis indeksów wtórnych w Redisie (np. `email:<x>→id`)
- [ ] Skrypt `switch_variant.sh <idx|no_idx>` – przełączanie stanu bazy

### 🤖 Automatyzacja benchmarku

- [ ] **Struktura katalogu `benchmarks/`**
  ```
  benchmarks/
  ├── __init__.py
  ├── runner.py              # orchestrator
  ├── config.py              # parametry (bazy, rozmiary, próby)
  ├── adapters/
  │   ├── mysql_adapter.py
  │   ├── postgres_adapter.py
  │   ├── mongo_adapter.py
  │   └── redis_adapter.py
  ├── scenarios/
  │   ├── create/ c1.py … c6.py
  │   ├── read/   r1.py … r6.py
  │   ├── update/ u1.py … u6.py
  │   └── delete/ d1.py … d6.py
  └── results/               # CSV z wynikami
  ```
- [ ] **Runner** uruchamia: 24 scen. × 4 bazy × 3 rozmiary × 3 próby × 2 warianty ≈ **1728 pomiarów**
- [ ] Zapis do CSV: `scenario_id, db, size, variant, run_no, duration_ms, rows_affected, plan_hash`
- [ ] Rozgrzewka (warm-up) przed każdą serią
- [ ] Reset cache między wariantami (opcja `--cold-cache`)

### 📊 Analiza planów zapytań (EXPLAIN)

- [ ] Dla każdego scenariusza READ (R1–R6) – zapisać plan `EXPLAIN ANALYZE` (PG, MySQL) i `.explain("executionStats")` (Mongo)
- [ ] Katalog `explain_plans/` z plikami tekstowymi per scenariusz + baza + wariant
- [ ] Krótka analiza planów w sprawozdaniu (różnice IDX vs NO_IDX)

### 📈 Wizualizacje wyników

- [ ] **Wykresy słupkowe grupowane** per (scenariusz, rozmiar) – IDX vs NO_IDX, 4 bazy
- [ ] **Heatmapa** średnich czasów (scenariusz × baza)
- [ ] **Wykresy skalowania** (S/M/L na osi X, czas na osi Y) per scenariusz
- [ ] Zapis do `reports/figures/*.png`
- [ ] Notebook `analysis.ipynb` z wszystkimi wykresami

### ✍️ Rozszerzona analiza wyników

- [ ] Sekcja w sprawozdaniu (~5–8 stron) z interpretacją:
  - [ ] Gdzie indeksy najbardziej pomogły? (najgorzej zaszkodziły?)
  - [ ] Który silnik wygrywa per operacja?
  - [ ] Jak wydajność skaluje się z rozmiarem danych?
  - [ ] Wnioski dla architekta systemu OLTP

---

## Poziom 5.0 – elementy zaawansowane

> Wymagane jest wykonanie **co najmniej 2 z 4** poniższych punktów **oraz** hipotezy badawczej.

### ⭐ Wybrane (MUST HAVE)

#### 1. Automatyzacja testów i generowania wyników
- [ ] CLI `python -m benchmarks.runner --scenario all --db all --size all --variant both --runs 3`
- [ ] Generowanie raportu HTML/PDF `python -m benchmarks.report`
- [ ] Integracja z GitHub Actions (opcjonalnie) – smoke test na małym zbiorze

#### 2. Dane półustrukturalne (JSON)
- [ ] Scenariusz U4 – modyfikacja `specs` (JSON/JSONB/embedded)
- [ ] Porównanie: `TEXT` (obecny) vs `JSON` (MySQL) vs `JSONB` (PG) vs Mongo embedded
- [ ] Indeks GIN w PG (`jsonb_path_ops`) + wyszukiwanie po polu JSON
- [ ] Osobna sekcja w sprawozdaniu z przykładami zapytań i wynikami

### 🎯 Opcjonalne (NICE TO HAVE – dodatkowo punktowane)

#### 3. Testy skalowalności
- [ ] Scenariusz równoległy – 1 / 10 / 100 wątków
- [ ] Narzędzia: `pgbench`, `sysbench`, lub własny worker pool
- [ ] Metryki: throughput (ops/s), latencja p50/p95/p99

#### 4. Analiza bezpieczeństwa
- [ ] Utworzenie ról (admin, app, readonly)
- [ ] `GRANT`/`REVOKE` per scenariusz
- [ ] TLS pomiędzy klientem a bazą
- [ ] Porównanie czasu CRUD z/bez szyfrowania

---

## Hipoteza badawcza

**H1: Indeksy a wydajność** (wybrana)

> Zastosowanie indeksów znacząco poprawia wydajność operacji SELECT kosztem spadku wydajności operacji INSERT i UPDATE.

- [ ] Sformułowanie hipotezy w sprawozdaniu (kontekst, motywacja)
- [ ] Metodyka weryfikacji (porównanie IDX vs NO_IDX w 24 scenariuszach)
- [ ] Wyniki – tabele + wykresy
- [ ] **Wniosek:** potwierdzamy / odrzucamy / częściowo potwierdzamy H1
- [ ] Dyskusja – kiedy hipoteza *nie* zachodzi (np. Redis, małe zbiory)

---

## Produkty końcowe

### 📄 Sprawozdanie pisemne (PDF, ~30–50 stron)

Struktura:
1. Strona tytułowa + abstrakt
2. Cel i zakres pracy
3. Opis SZBD (4 silniki)
4. Charakterystyki teoretyczne (awaryjność, bezpieczeństwo, ...)
5. Obszary zastosowań
6. Opis zbioru danych + ERD
7. Opis aplikacji testowej
8. Metodyka testów
9. 24 scenariusze testowe (streszczenie)
10. Wyniki – tabele + wykresy
11. Analiza planów zapytań
12. Indeksowanie – wyniki IDX vs NO_IDX
13. Dane półustrukturalne (JSON)
14. Hipoteza badawcza – weryfikacja
15. Wnioski i dyskusja
16. Bibliografia

### 🎤 Prezentacja (slajdy, 15–20 min)

- [ ] Wprowadzenie (2 slajdy) – cel, zespół, zakres
- [ ] SZBD w projekcie (2) – krótki opis każdego
- [ ] Schemat i dane (2) – ERD, rozmiary
- [ ] Metodyka (1) – 1728 pomiarów, IDX vs NO_IDX
- [ ] Najciekawsze wyniki (5–7) – wykresy z highlightami
- [ ] Hipoteza + weryfikacja (2)
- [ ] Wnioski + Q&A (1–2)

### 📋 Dokumentacja repozytorium

- [ ] Zaktualizować `README.md` (instrukcja uruchomienia, struktura repo)
- [ ] Dodać `requirements.txt` (Python deps)
- [ ] `Makefile` z komendami: `make up`, `make generate SIZE=m`, `make import`, `make benchmark`, `make report`

---

## Harmonogram i kolejność prac

> Poniżej kolejność minimalizująca ryzyko – każdy punkt odblokowuje następne.

| # | Zadanie | Output | Zależności |
|--:|---|---|---|
| 1 | Sparametryzowanie generatora (S/M/L) | `data/{s,m,l}/*.csv` | – |
| 2 | Pliki indeksów (`indexes.sql`, `indexes_drop.sql`, `indexes_mongo.js`) | – | – |
| 3 | Adaptery do 4 baz w `benchmarks/adapters/` | API: `execute(sql)`, `time_it()` | 1, 2 |
| 4 | Implementacja 24 scenariuszy w `benchmarks/scenarios/` | Moduły Pythonowe | 3 |
| 5 | Runner + CLI | `benchmarks/runner.py` | 4 |
| 6 | Pełny run benchmarku (1728 pomiarów) | `results/*.csv` | 5 |
| 7 | Zebranie planów zapytań EXPLAIN | `explain_plans/*.txt` | 6 |
| 8 | Analiza + wykresy (notebook) | `reports/figures/*.png` | 6 |
| 9 | Sprawozdanie – sekcje teoretyczne (3.0) | `report.md` → PDF | – (równolegle) |
| 10 | Sprawozdanie – sekcje wynikowe (4.0/5.0) | jw. | 7, 8 |
| 11 | Prezentacja | `slides.pdf` | 10 |
| 12 | Finalizacja repo + README | – | 1–11 |

---

## Podział zadań w zespole

> Wymóg regulaminu §3: harmonogram prac + podział zadań przypisany do każdej osoby.

**Propozycja dla zespołu 2-osobowego:**

| Osoba | Zakres |
|---|---|
| **Osoba A (backend/data)** | Generator, indeksy, adaptery MySQL + PG, scenariusze CREATE + READ, sprawozdanie pkt 3, 6–11 |
| **Osoba B (nosql/analysis)** | Adaptery Mongo + Redis, scenariusze UPDATE + DELETE, notebook analityczny, wykresy, sprawozdanie pkt 4, 13–15 |
| **Wspólnie** | Runner, hipoteza H1, prezentacja, finalizacja repo |

**Dla zespołu 3-osobowego** – dołożyć osobę odpowiedzialną za część teoretyczną (pkt 3–7 sprawozdania) oraz formatowanie dokumentów.

---

## Szybka ściągawka „co teraz?"

1. **Dzisiaj** → Zadanie #1 i #2 (generator + indeksy) — razem ~1 wieczór
2. **Jutro** → Zadanie #3 i #4 (adaptery + scenariusze) — 2–3 wieczory
3. **Ten tydzień** → Zadanie #5 i #6 (runner + benchmark) — 1 wieczór + 1 doba CPU
4. **Przyszły tydzień** → Zadania #7–#10 (analiza + sprawozdanie)
5. **Przed terminem** → Zadania #11–#12 (prezentacja + finalizacja)

---

**Regulamin referencja:** `Regulamin zajęć ZTB_25-26_dzienne.pdf` — §3 pkt 2 (ocena 5.0 = wymagania 4.0 + min. 2 elementy zaawansowane + hipoteza).
