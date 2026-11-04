# Excluded from current training manifests

- `SHARED/plantdoc_classification`: archive is retained, but Windows cannot
  extract source filenames containing `?` without renaming source files.
- `SHARED/plantdoc_detection`: same Windows filename restriction.
- `CHILLI/chilli_leaf_disease/cercospora_field_unattributed`: ZIP CRC failure
  for `IMG_20250615_162246.jpg`; retain the archive and do not train on it.
- `CHILLI/other_chilli_datasets/chilli_nested_rar_unattributed`: contains nested
  RAR files; no extraction or label validation has been completed.
- Task-specific detection datasets and unattributed collections are preserved
  but excluded from the baseline classification manifests until their labels,
  licence, and annotation conventions are validated.
