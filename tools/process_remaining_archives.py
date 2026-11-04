"""Sequential restartable batch for the remaining top-level Tomato/Chilli archives."""
from __future__ import annotations

import csv
import os
import subprocess
import sys
from pathlib import Path

from organize_shared_inbox import sha256

ROOT = Path(r"C:\Users\Nithin\Downloads\cropscope_shared_downloader\DATASET_INBOX")
PROJECT = Path(r"C:\Projects\The Dirt Bags")
PYTHON = PROJECT / ".venv" / "Scripts" / "python.exe"
PROCESSOR = PROJECT / "tools" / "process_archive.py"

JOBS = [
    (ROOT / "dataset tomato" / "Multiclass Image Dataset of Tomato Pathologies Int.zip", PROJECT / "DATASETS" / "TOMATO" / "tomato_disease" / "tomato_pathologies_multiclass_unattributed"),
    (ROOT / "dataset tomato" / "TomatoPlantfactoryDataset.zip", PROJECT / "DATASETS" / "TOMATO" / "tomato_disease" / "tomato_plantfactory_unattributed"),
    (ROOT / "dataset chilli" / "Anthracnose.zip", PROJECT / "DATASETS" / "CHILLI" / "chilli_leaf_disease" / "anthracnose_field_unattributed"),
    (ROOT / "dataset chilli" / "Cercospora Leaf Spot.zip", PROJECT / "DATASETS" / "CHILLI" / "chilli_leaf_disease" / "cercospora_field_unattributed"),
    (ROOT / "dataset chilli" / "Fresh Leaf.zip", PROJECT / "DATASETS" / "CHILLI" / "chilli_leaf_disease" / "healthy_leaf_field_unattributed"),
    (ROOT / "dataset chilli" / "Leaf Curl Disease.zip", PROJECT / "DATASETS" / "CHILLI" / "chilli_leaf_disease" / "leaf_curl_field_unattributed"),
    (ROOT / "dataset chilli" / "archive.zip", PROJECT / "DATASETS" / "CHILLI" / "chilli_leaf_disease" / "chilli_plant_diseases_augmented_unattributed"),
    (ROOT / "dataset chilli" / "chilli dataset.zip", PROJECT / "DATASETS" / "CHILLI" / "other_chilli_datasets" / "chilli_nested_rar_unattributed"),
    (ROOT / "dataset chilli" / "Chilli_MVP" / "Chilli_MVP" / "data" / "raw" / "CH-001_v3.zip", PROJECT / "DATASETS" / "CHILLI" / "chilli_leaf_disease" / "ch001_mendeley_v3"),
]


def main() -> None:
    if os.environ.get("CROPSCOPE_ALLOW_SOURCE_ARCHIVE_DELETE") != "YES":
        raise SystemExit(
            "Disabled by default: this legacy script deletes verified source archives. "
            "Use the non-destructive Chilli preparation tools instead."
        )
    log_rows: list[dict[str, str]] = []
    for source, dataset in JOBS:
        if not source.exists():
            log_rows.append({"source": str(source), "dataset": str(dataset), "status": "SKIPPED_SOURCE_NOT_PRESENT"})
            continue
        result = subprocess.run([str(PYTHON), str(PROCESSOR), "--source", str(source), "--dataset", str(dataset)], cwd=PROJECT, text=True, capture_output=True)
        copied = dataset / "downloads" / source.name
        if result.returncode == 0 and copied.exists() and sha256(source) == sha256(copied):
            source.unlink()
            status = "SUCCESS_SOURCE_DELETED"
        else:
            status = "FAILED_SOURCE_RETAINED"
        log_rows.append({"source": str(source), "dataset": str(dataset), "status": status, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()})
        print(f"{status}: {source.name}", flush=True)
    with (PROJECT / "DATASETS" / "remaining_batch_report.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source", "dataset", "status", "stdout", "stderr"])
        writer.writeheader(); writer.writerows(log_rows)
    failures = [row for row in log_rows if row["status"] == "FAILED_SOURCE_RETAINED"]
    sys.exit(2 if failures else 0)


if __name__ == "__main__":
    main()
