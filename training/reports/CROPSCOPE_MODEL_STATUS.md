# CropScope model status

## Completed

| Model | Data | Held-out test result | Location |
|---|---|---:|---|
| CH-001 Chilli original MobileNetV3 | Six original CH-001 classes only | macro-F1 0.992979 | `training/outputs/chilli_baseline` |
| Tomato PlantVillage MobileNetV3 | Nine documented Tomato disease/healthy classes; pests excluded | macro-F1 0.991867, accuracy 0.993528 | `training/outputs/tomato_plantvillage_20261105` |

## Not trained responsibly

- Tomato Tuta detection: source has `file_labels.csv` image-level labels; no verified bounding-box or segmentation annotations. Detection training is blocked.
- Liriomyza: no local usable source was discovered.
- Mixed infestation: no verified co-occurrence annotation was discovered.
- CH-001 augmented comparison: not trained; augmentation-to-original grouping has not been independently validated, so it cannot safely enter an unbiased split.
- General multi-crop and general pest models: deferred pending taxonomy/source audit; no labels were merged on name similarity.

Both completed models used RTX 3050 Laptop GPU, CUDA AMP and untouched held-out test splits. Raw data was not modified.

## Active / blocked

- **Tuta binary FAST EXPERIMENT:** active local CUDA run at `training/outputs/tuta_binary_20261105`. CSV-ground-truth manifest: 4,341 images (2,336 Healthy, 2,005 affected), split 3,039/651/651. It is strictly image-level classification, not detection. No exact duplicate or corrupt labelled files were found.
- **PlantVillage-to-PlantWild screening:** evaluation script prepared at `training/evaluate_external_tomato.py`; it will run after the sole active GPU job ends.
- **Liriomyza:** BLOCKED. Read-only local dataset/document scan found no verified Liriomyza/leaf-miner image labels or annotations.
- **PlantDoc Tomato field model:** BLOCKED. The local PlantDoc classification extraction has only a partial test hierarchy, no train directory, and no Tomato class folders; it is not a valid training source.
- **Extended Chilli model:** BLOCKED. Extra field sources are unattributed and the augmented source uses a different taxonomy; merging them into the six-class CH-001 task would fabricate label compatibility.
- **IP102:** READY_FOR_SEPARATE_PEST_EXPERIMENT. Local classification image tar/source and VOC annotation/image data are present, but it is intentionally not started while Tuta owns the single GPU.
