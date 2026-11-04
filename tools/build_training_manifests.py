"""Build no-copy, deterministic classification manifests from validated raw datasets."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(r"C:\Projects\The Dirt Bags\DATASETS")
OUT = ROOT / "TRAINING_READY"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}

SOURCES = {
    "plantvillage_color": ROOT / "SHARED" / "plantvillage" / "extracted" / "PlantVillage_data" / "raw" / "color",
    "plantwild": ROOT / "SHARED" / "plantwild" / "extracted" / "plantwild" / "plantwild" / "images",
    "olid_i": ROOT / "SHARED" / "olid_i" / "extracted",
    "ch001_original": ROOT / "CHILLI" / "chilli_leaf_disease" / "ch001_mendeley_v3" / "extracted" / "Chili Leaf Disease Original Dataset" / "Chili Leaf Disease Original Dataset",
}


def split_for(key: str) -> str:
    value = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16) % 100
    return "train" if value < 70 else "validation" if value < 85 else "test"


def label_for(dataset: str, path: Path) -> str | None:
    if dataset in {"plantvillage_color", "plantwild", "ch001_original"}:
        return path.parent.name
    if dataset == "olid_i":
        # Original parts use class directories immediately below each part root.
        for parent in path.parents:
            if parent.parent.name.startswith("part_"):
                return parent.name
    return None


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    summary = []
    for dataset, root in SOURCES.items():
        rows = []
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in IMAGE_EXTS or "__MACOSX" in path.parts:
                continue
            label = label_for(dataset, path)
            if not label:
                continue
            relative = path.relative_to(ROOT).as_posix()
            rows.append({"dataset_id": dataset, "relative_path": relative, "label": label, "split": split_for(f"{dataset}:{relative}")})
        rows.sort(key=lambda row: (row["label"], row["relative_path"]))
        with (OUT / f"{dataset}_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["dataset_id", "relative_path", "label", "split"])
            writer.writeheader(); writer.writerows(rows)
        counts = Counter(row["split"] for row in rows)
        summary.append({"dataset_id": dataset, "images": len(rows), "classes": len({row["label"] for row in rows}), **counts, "manifest": f"{dataset}_manifest.csv"})
    with (OUT / "MANIFEST_SUMMARY.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=2)
    (OUT / "README.md").write_text("# Training-ready manifests\n\nThese CSV manifests provide deterministic 70/15/15 path-based splits without copying or modifying raw images. They deliberately include only validated extraction sources: PlantVillage colour images, PlantWild, OLID-I, and CH-001 original images. Augmented CH-001 images, failed/corrupt archives, and task-specific detection datasets are excluded pending dedicated validation.\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
