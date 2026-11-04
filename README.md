# CropScope AI dataset collection workspace

This repository is for collecting and documenting original datasets only. It contains no application, backend, model, training, GPU, Docker, or automation setup.

## Dataset-handling rules

1. Put every downloaded original archive in that dataset's `downloads/` folder.
2. Extract the archive into the corresponding `extracted/` folder.
3. Preserve the original folder hierarchy, class names, annotations, and filenames.
4. Never resize, rename, augment, delete, or modify original images.
5. Never combine datasets from different sources into one directory.
6. Never duplicate multi-crop datasets across individual crop folders; keep them under `DATASETS/SHARED/`.
7. Record the verified source URL and license in that dataset's `SOURCE.md`.
8. Update `DATASET_INVENTORY.csv` after every download, extraction, or verification.
9. If a dataset has multiple versions, preserve its version information.
10. Do not treat augmented images as independent original samples.
11. For Liriomyza and mixed infestation, distinguish confirmed expert-labelled images from unverified internet images.

## Where downloads belong

- Tomato datasets: `DATASETS/TOMATO/<dataset>/downloads/`
- Chilli datasets: `DATASETS/CHILLI/<dataset>/downloads/`
- General and multi-crop datasets: `DATASETS/SHARED/<dataset>/downloads/`

Extract each archive only into its sibling `extracted/` folder. Raw archives and extracted data are intentionally excluded from Git; the documentation and inventory remain version controlled.
