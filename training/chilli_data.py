"""Portable, immutable preparation for the CH-001 original Chilli dataset."""
from __future__ import annotations

import csv
import hashlib
import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

CLASS_NAMES = ["Bacterial Spot", "Cercospora Leaf Spot", "Curl Virus", "Healthy Leaf", "Nutrition Deficiency", "White spot"]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
MANIFEST_FIELDS = ["dataset_id", "relative_path", "label", "class_index", "split", "sha256"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_image(path: Path) -> tuple[bool, str | None]:
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.load()
        return True, None
    except (UnidentifiedImageError, OSError, ValueError) as error:
        return False, f"unreadable_image:{type(error).__name__}"


def class_split_counts(total: int) -> dict[str, int]:
    if total < 3:
        raise ValueError(f"Class has only {total} usable images; at least 3 are required for train/validation/test.")
    validation, test = max(1, round(total * 0.15)), max(1, round(total * 0.15))
    train = total - validation - test
    if train < 1:
        raise ValueError(f"Class has insufficient images for a non-empty training split: {total}")
    return {"train": train, "validation": validation, "test": test}


def stratified_split(rows: list[dict[str, str]], seed: int) -> list[dict[str, str]]:
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[row["label"]].append(row)
    output: list[dict[str, str]] = []
    for label in CLASS_NAMES:
        ordered = sorted(groups[label], key=lambda row: row["relative_path"])
        counts = class_split_counts(len(ordered))
        random.Random(f"{seed}:{label}").shuffle(ordered)
        for index, row in enumerate(ordered):
            row["split"] = "train" if index < counts["train"] else "validation" if index < counts["train"] + counts["validation"] else "test"
            output.append(row)
    return sorted(output, key=lambda row: (row["split"], row["label"], row["relative_path"]))


def build_chilli_manifest(dataset_root: Path, output_dir: Path, seed: int = 42, smoke_limit_per_class: int | None = None) -> dict[str, Any]:
    dataset_root, output_dir = dataset_root.expanduser().resolve(), output_dir.expanduser().resolve()
    if not dataset_root.is_dir():
        raise FileNotFoundError(f"Dataset root does not exist: {dataset_root}")
    actual = sorted(path.name for path in dataset_root.iterdir() if path.is_dir() and not path.name.startswith("."))
    if actual != sorted(CLASS_NAMES):
        raise ValueError(f"Expected exactly {CLASS_NAMES}; found {actual}")
    output_dir.mkdir(parents=True, exist_ok=True)
    class_to_idx = {label: index for index, label in enumerate(CLASS_NAMES)}
    skipped: list[dict[str, str]] = []
    candidates: list[dict[str, str]] = []
    for label in CLASS_NAMES:
        files = sorted((path for path in (dataset_root / label).rglob("*") if path.is_file()), key=lambda path: path.as_posix())
        if smoke_limit_per_class is not None:
            files = files[:smoke_limit_per_class]
        for path in files:
            relative = path.relative_to(dataset_root).as_posix()
            if path.name.startswith(".") or path.name == ".DS_Store" or "__MACOSX" in path.parts:
                skipped.append({"relative_path": relative, "reason": "hidden_or_metadata"}); continue
            if path.suffix.lower() not in IMAGE_EXTENSIONS:
                skipped.append({"relative_path": relative, "reason": "non_image_extension"}); continue
            okay, reason = valid_image(path)
            if not okay:
                skipped.append({"relative_path": relative, "reason": reason or "unreadable_image"}); continue
            candidates.append({"dataset_id": "chilli_ch001_original_v3", "relative_path": relative, "label": label, "class_index": str(class_to_idx[label]), "sha256": sha256_file(path)})
    hash_labels: dict[str, set[str]] = defaultdict(set)
    for row in candidates:
        hash_labels[row["sha256"]].add(row["label"])
    selected: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in candidates:
        key = (row["label"], row["sha256"])
        if len(hash_labels[row["sha256"]]) > 1:
            skipped.append({"relative_path": row["relative_path"], "reason": "cross_class_exact_duplicate"})
        elif key in seen:
            skipped.append({"relative_path": row["relative_path"], "reason": "within_class_exact_duplicate"})
        else:
            seen.add(key); selected.append(row)
    manifest = stratified_split(selected, seed)
    distribution = []
    for label in CLASS_NAMES:
        row: dict[str, Any] = {"label": label, "class_index": class_to_idx[label], "usable_images": sum(item["label"] == label for item in manifest)}
        row.update({split: sum(item["label"] == label and item["split"] == split for item in manifest) for split in ("train", "validation", "test")})
        distribution.append(row)
    with (output_dir / "chilli_ch001_original_manifest.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS); writer.writeheader(); writer.writerows(manifest)
    with (output_dir / "chilli_class_distribution.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["label", "class_index", "usable_images", "train", "validation", "test"]); writer.writeheader(); writer.writerows(distribution)
    quality = {"generated_utc": datetime.now(timezone.utc).isoformat(), "dataset_root": str(dataset_root), "raw_files_scanned": sum(1 for path in dataset_root.rglob("*") if path.is_file()), "valid_candidates": len(candidates), "included_images": len(manifest), "skipped_count": len(skipped), "skipped": skipped, "cross_class_duplicate_hashes": sum(len(labels) > 1 for labels in hash_labels.values())}
    summary = {"dataset_id": "chilli_ch001_original_v3", "seed": seed, "classes": CLASS_NAMES, "counts_by_split": dict(Counter(row["split"] for row in manifest)), "counts_by_class": distribution, "manifest": "chilli_ch001_original_manifest.csv"}
    (output_dir / "chilli_data_quality_report.json").write_text(json.dumps(quality, indent=2), encoding="utf-8")
    (output_dir / "chilli_split_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output_dir / "class_to_idx.json").write_text(json.dumps(class_to_idx, indent=2), encoding="utf-8")
    return summary
