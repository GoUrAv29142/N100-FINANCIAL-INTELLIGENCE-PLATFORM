# Sprint 1 Demonstration

## Pipeline

Raw Excel Files
        ↓
Loader
        ↓
Normalizer
        ↓
Validator
        ↓
SQLite Loader
        ↓
SQLite Database
        ↓
SQL Queries

---

## Demonstration Steps

1. Run ETL pipeline
2. Generate validation report
3. Generate load audit
4. Verify database
5. Execute exploratory SQL queries
6. Run unit tests

---

## Results

- 92 companies loaded
- 0 foreign key violations
- 0 critical validation failures
- 38 unit tests passed