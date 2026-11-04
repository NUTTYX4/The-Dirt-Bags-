# Datasets

`DATASETS/` is the project's local raw-data store. It contains source archives,
their preserved extractions, integrity records, and lightweight documentation.

## Rules

- Keep original archives and supplied supplementary files under each dataset's
  `downloads/` directory without renaming them.
- Extract only after a copied archive is verified; preserve its original
  hierarchy beneath `extracted/`.
- Store source evidence, checksums, inventories, and reports in `metadata/` and
  the dataset-level Markdown files.
- Do not modify, deduplicate, relabel, resize, or overwrite raw source data.
- Raw archives and extracted content are ignored by Git.  Reports and metadata
  remain suitable for version control.

## Training preparation

`TRAINING_READY/` contains deterministic, path-only train/validation/test
manifests. The generated CSV/JSON files are intentionally Git-ignored because
they are derived local artifacts; rerun `tools/build_training_manifests.py` to
create them after cloning and restoring the raw datasets.

## Current state

See `ORGANIZATION_REPORT.md`, `EXTRACTION_REPORT.md`, and
`_REVIEW_REQUIRED/EXCLUDED_DATASETS.md` for completed processing and known
exceptions.

`_REVIEW_REQUIRED/` is only for material whose source and category cannot be
established from evidence; it is not a dataset category.
