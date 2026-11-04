# Dataset audit

This audit records only sources safe enough for the current training decisions. Raw source structures and archives remain untouched.

- CH-001 original was validated during manifest creation: 1,842 usable images after excluding 14 cross-class exact-duplicate samples. It is the completed six-class baseline.
- PlantVillage Tomato was validated into a 16,470-image source-specific, nine-class disease/healthy manifest. The spider-mite class was intentionally excluded.
- PlantWild Tomato is reserved as a possible external source; its ambiguous `tomato leaf` class was not merged.
- Tuta has an image-level `file_labels.csv`, not verified localisation labels. No detection model was fabricated.
- No usable local Liriomyza source was found.
