# Organization Report

## Initial inspection — 2026-11-04

- Project root inspected: `C:\Projects\The Dirt Bags`
- Existing legacy scaffold found: `DATASETS/`; it contains directory markers
  and template source files only. It was not altered.
- Source inbox inspected read-only:
  `C:\Users\Nithin\Downloads\cropscope_shared_downloader\DATASET_INBOX`.
- Source archives found: 46 archives, totalling 76,811,237,562 bytes
  (71.54 GiB). These include a complete 19-part OLID-I collection and source
  archives for PlantVillage, PlantDoc (classification and detection),
  PlantWild, IP102, VegHealth14, loose Chilli datasets, and loose Tomato
  datasets.
- Source documentation found for all supplied SHARED datasets. Its final
  downloader report says all 19 OLID-I parts passed official MD5 verification
  (with part 13 verified using Zenodo's authoritative checksum) and PlantWild
  passed a recorded SHA-256 verification.
- The source's VegHealth14 `SOURCE.md` says it was pending, but a VegHealth14
  archive is actually present. The final inventory must report that discrepancy
  accurately after archive validation.
- Chilli material includes an embedded `.venv` inside `Chilli_MVP`; environment
  files are not source dataset material and will not be copied or inventoried.
- The Tomato and Chilli loose archives need source/contents correlation before
  a destination is assigned; filenames alone will not be treated as evidence.

## Created inbox structure

Created `DATASET_INBOX/` with planned SHARED, TOMATO, and CHILLI destinations,
each with `downloads/`, `extracted/`, and `metadata/` subdirectories. No
dataset-specific identity has been asserted and no raw data has been copied,
renamed, extracted, or deleted.

`SHARED/veghealth14/` is a planned placeholder. Its status is
`PENDING_AUTHENTICATED_DOWNLOAD` until a real archive and source evidence are
provided.

## Storage blocker

The source and project are both on `C:`. At inspection time, `C:` had only
78.28 GiB free. A raw copy of the 71.54 GiB archive collection would leave
approximately 6.74 GiB before any extraction, which is insufficient and risks
an incomplete data transfer. No archive has been copied, extracted, renamed,
or deleted.

## Next operation

Provide a destination volume with enough free space for both the verified raw
copies and their extracted contents, or explicitly authorize a different
storage strategy. Then correlate loose Tomato and Chilli archives with their
evidence, copy, checksum, validate, extract, and inventory each verified
dataset without overwriting completed work.
