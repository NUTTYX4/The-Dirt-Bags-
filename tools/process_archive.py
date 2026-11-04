"""Copy one source archive, verify it, safely extract it, and write restartable records."""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from pathlib import Path

from organize_shared_inbox import extract_tar, extract_zip, sha256


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--extra", type=Path, action="append", default=[])
    args = parser.parse_args()
    source = args.source.resolve()
    dataset = args.dataset.resolve()
    if not source.is_file():
        raise SystemExit(f"Source file not found: {source}")
    downloads, extracted, metadata = (dataset / "downloads", dataset / "extracted", dataset / "metadata")
    for folder in (downloads, extracted, metadata):
        folder.mkdir(parents=True, exist_ok=True)
    copied = downloads / source.name
    source_hash = sha256(source)
    if not copied.exists() or sha256(copied) != source_hash:
        shutil.copy2(source, copied)
    copied_hash = sha256(copied)
    if copied_hash != source_hash:
        raise SystemExit("Copied SHA-256 does not match source; source retained.")
    for extra in args.extra:
        if not extra.is_file():
            raise SystemExit(f"Supplementary file not found: {extra}")
        destination = downloads / extra.name
        if not destination.exists() or sha256(destination) != sha256(extra):
            shutil.copy2(extra, destination)
    output = extracted / source.stem
    marker = output / ".extraction_complete.json"
    status, details, count, size = "SUCCESS", "existing completion marker", 0, 0
    if not marker.exists():
        try:
            output.mkdir(parents=True, exist_ok=True)
            if source.suffix.lower() == ".zip":
                count, size = extract_zip(copied, output)
            else:
                count, size = extract_tar(copied, output)
            marker.write_text(json.dumps({"archive": copied.name, "file_count": count, "size_bytes": size}, indent=2), encoding="utf-8")
            details = "validated and extracted"
        except Exception as error:
            status, details = "FAILED", f"{type(error).__name__}: {error}"
    with (metadata / "archive_checksums.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["filename", "size_bytes", "source_sha256", "copied_sha256", "integrity_status"])
        writer.writeheader(); writer.writerow({"filename": source.name, "size_bytes": source.stat().st_size, "source_sha256": source_hash, "copied_sha256": copied_hash, "integrity_status": "MATCH"})
    (dataset / "EXTRACTION_REPORT.md").write_text(f"# Extraction Report\n\n- `{copied.name}` — {status}; {details}\n", encoding="utf-8")
    (metadata / "source_metadata.json").write_text(json.dumps({"source_path": str(source), "source_sha256": source_hash, "copied_archive": str(copied), "extraction_status": status}, indent=2), encoding="utf-8")
    print(json.dumps({"status": status, "source": str(source), "destination": str(copied), "extracted_file_count": count, "extracted_size_bytes": size, "details": details}))
    sys.exit(0 if status == "SUCCESS" else 2)


if __name__ == "__main__":
    main()
