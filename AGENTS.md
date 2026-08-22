# AGENTS.md

## Data Management

- Never edit raw dataset contents in place.
- Preserve data provenance, including original filename, source organization,
  source URL when known, download date, data period, and geographic scope.
- Use English lowercase `snake_case` filenames for datasets.
- Treat `data/raw/` as immutable source material. Raw files may be renamed,
  categorized, or moved, but not cleaned, filtered, joined, or otherwise changed
  in place.
- Derived datasets must be reproducible from code whenever possible.
- Any script that transforms data should write results to `data/interim/` or
  `data/processed/`, never overwrite `data/raw/`.
- When adding a new external dataset, update `data/data_catalog.csv`.
