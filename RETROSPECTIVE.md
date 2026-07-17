# Sprint 1 Retrospective

## What went well

- Successfully developed an end-to-end ETL pipeline.
- Implemented normalization and validation modules.
- Loaded all datasets into SQLite with referential integrity.
- Achieved 38/38 passing unit tests.
- Manual review identified ABB/Abbott India mapping issue.
- Validator detected duplicate financial ratio records before loading.
- Environment setup and dependency issues were resolved.

---

## Challenges

- Source Excel files contained inconsistent company names.
- Bank financial statements use different formats from industrial companies.
- Expected row counts differed because only 92 companies were available.
- Documentation listed "10 tables" while schema contains 11 tables.

---

## Improvements

- Add automatic company-name matching.
- Add outlier detection for abnormal financial ratios.
- Implement dedicated bank financial statement parser.
- Improve validation rules for financial ratios.

---

## Lessons Learned

Automated validation is essential but should be complemented by manual data review to identify structural data issues that are difficult to detect through rules alone.