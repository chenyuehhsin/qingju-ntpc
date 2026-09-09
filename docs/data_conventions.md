# Data Conventions

This project keeps source data traceable and reproducible. Treat files under
`data/raw/` as immutable source material.

## Data Layers

- `data/raw/`: Original external datasets. Files may be renamed, categorized,
  or moved, but their contents must not be edited in place.
- `data/interim/`: Temporary or intermediate outputs from cleaning, filtering,
  joins, parsing, or exploration.
- `data/processed/`: Final datasets used by the dashboard, API, model, or other
  application code.

Derived data must not overwrite raw files. When possible, derived datasets
should be reproducible from scripts or notebooks committed to the repository.

## File Naming

- Use English lowercase `snake_case`.
- Do not use spaces, Chinese punctuation, or vague names such as `final.csv`,
  `new.csv`, or `data2.csv`.
- Include a source or organization prefix when useful, such as `ntpc` or `moi`.
- Include dates in ISO format: `YYYY-MM-DD` for download or snapshot dates, and
  `YYYY-MM` for monthly statistic periods.
- Keep source context in `data/data_catalog.csv` so renaming does not remove
  provenance.

## Adding New Raw Data

1. Save the downloaded file outside `data/raw/` first.
2. Register it with `scripts/register_raw_data.py`, or manually place it under
   the correct `data/raw/<category>/` directory using an English snake_case
   filename.
3. Add or update the record in `data/data_catalog.csv`.
4. Record the original filename, source organization, source URL if known,
   download date, data period, geographic scope, and notes.
5. Put any cleaned or joined outputs in `data/interim/` or `data/processed/`.

## Provenance

Provenance metadata makes the dataset auditable: teammates should be able to
identify where a file came from, when it was downloaded, which time period it
describes, and whether it is raw or derived. This prevents confusion when
multiple agencies publish similar tables or when files are renamed for GitHub
collaboration.

## New Versions

For a newer release of the same dataset, add a new dated file instead of
overwriting the old raw file. For example:

```text
data/raw/housing/ntpc_rental_transactions_2026-08-21.csv
data/raw/housing/ntpc_rental_transactions_2026-09-01.csv
```

Add a separate catalog record for each version. Derived outputs can then choose
which raw version they depend on.

## Why Raw Files Stay Unchanged

Raw files are the baseline for checking data quality, reproducing transformations,
and debugging results. Editing raw files in place makes it hard to know whether a
value came from the source agency or from project-side processing.
