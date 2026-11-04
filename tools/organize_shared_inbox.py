"""Copy, verify, and safely extract the documented SHARED source datasets.

The script is deliberately restartable: a destination file with the same
SHA-256 is reused, and a completed extraction has a marker file.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import tarfile
import time
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
ARCHIVE_EXTENSIONS = {".zip", ".tar", ".gz", ".tgz", ".xz", ".bz2"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_safe(member_name: str, target: Path) -> Path:
    name = member_name.replace("\\", "/")
    candidate = (target / name).resolve()
    if name.startswith("/") or ":" in Path(name).drive or os.path.commonpath((str(target.resolve()), str(candidate))) != str(target.resolve()):
        raise ValueError(f"unsafe archive member path: {member_name!r}")
    return candidate


def extract_zip(archive_path: Path, output: Path) -> tuple[int, int]:
    with zipfile.ZipFile(archive_path) as archive:
        encrypted = [entry.filename for entry in archive.infolist() if entry.flag_bits & 0x1]
        if encrypted:
            raise ValueError(f"encrypted ZIP entries: {len(encrypted)}")
        corrupt = archive.testzip()
        if corrupt:
            raise ValueError(f"ZIP CRC failure: {corrupt}")
        entries = [entry for entry in archive.infolist() if not entry.is_dir()]
        for entry in entries:
            destination = relative_safe(entry.filename, output)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(entry) as source, destination.open("wb") as destination_handle:
                shutil.copyfileobj(source, destination_handle, 8 * 1024 * 1024)
    return len(entries), sum(entry.file_size for entry in entries)


def extract_tar(archive_path: Path, output: Path) -> tuple[int, int]:
    with tarfile.open(archive_path) as archive:
        members = archive.getmembers()
        files = [member for member in members if member.isfile()]
        for member in members:
            if member.issym() or member.islnk():
                raise ValueError(f"symbolic link rejected: {member.name}")
            relative_safe(member.name, output)
        for member in files:
            destination = relative_safe(member.name, output)
            destination.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise ValueError(f"could not read TAR member: {member.name}")
            with source, destination.open("wb") as destination_handle:
                shutil.copyfileobj(source, destination_handle, 8 * 1024 * 1024)
    return len(files), sum(member.size for member in files)


def extraction_folder(dataset: str, archive: Path) -> str:
    if dataset == "olid_i" and archive.stem.startswith("part_"):
        return f"part_{int(archive.stem.split('_')[1]):02d}"
    return archive.stem


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    started = datetime.now(timezone.utc).isoformat()
    inventory: list[dict] = []
    extraction_rows: list[dict] = []

    for source_dataset in sorted(path for path in args.source.iterdir() if path.is_dir()):
        dataset = source_dataset.name
        destination_dataset = args.destination / "SHARED" / dataset
        downloads_source = source_dataset / "downloads"
        if not downloads_source.exists():
            continue
        downloads_destination = destination_dataset / "downloads"
        extracted_destination = destination_dataset / "extracted"
        metadata_destination = destination_dataset / "metadata"
        for directory in (downloads_destination, extracted_destination, metadata_destination):
            directory.mkdir(parents=True, exist_ok=True)

        source_document = source_dataset / "SOURCE.md"
        if source_document.exists():
            shutil.copy2(source_document, destination_dataset / "SOURCE.md")

        checksum_rows: list[dict] = []
        archive_rows: list[dict] = []
        for source_file in sorted(path for path in downloads_source.rglob("*") if path.is_file()):
            relative = source_file.relative_to(downloads_source)
            destination_file = downloads_destination / relative
            destination_file.parent.mkdir(parents=True, exist_ok=True)
            source_hash = sha256(source_file)
            copy_action = "COPIED"
            if destination_file.exists() and destination_file.is_file() and sha256(destination_file) == source_hash:
                copy_action = "ALREADY_PRESENT_VERIFIED"
            else:
                shutil.copy2(source_file, destination_file)
            destination_hash = sha256(destination_file)
            verified = source_hash == destination_hash
            checksum_rows.append({
                "relative_path": str(relative).replace("\\", "/"),
                "size_bytes": source_file.stat().st_size,
                "source_sha256": source_hash,
                "copied_sha256": destination_hash,
                "copy_status": copy_action,
                "integrity_status": "MATCH" if verified else "MISMATCH",
            })
            if source_file.suffix.lower() in ARCHIVE_EXTENSIONS:
                archive_rows.append({"source": source_file, "destination": destination_file, "verified": verified})

        for archive_row in archive_rows:
            archive = archive_row["destination"]
            folder = extracted_destination / extraction_folder(dataset, archive)
            marker = folder / ".extraction_complete.json"
            started_at = time.monotonic()
            status = "SKIPPED_COMPLETED" if marker.exists() else "NOT_RUN"
            detail = "existing completion marker"
            file_count = 0
            byte_count = 0
            if archive_row["verified"] and not marker.exists():
                try:
                    folder.mkdir(parents=True, exist_ok=True)
                    if archive.suffix.lower() == ".zip":
                        file_count, byte_count = extract_zip(archive, folder)
                    else:
                        file_count, byte_count = extract_tar(archive, folder)
                    marker.write_text(json.dumps({"archive": archive.name, "completed_utc": datetime.now(timezone.utc).isoformat(), "file_count": file_count, "size_bytes": byte_count}, indent=2), encoding="utf-8")
                    status, detail = "SUCCESS", "validated and extracted"
                except Exception as error:  # Preserve archive and partial output for investigation.
                    status, detail = "FAILED", f"{type(error).__name__}: {error}"
            extraction_rows.append({
                "dataset_id": dataset,
                "archive": str(archive.relative_to(destination_dataset)).replace("\\", "/"),
                "integrity_status": "MATCH" if archive_row["verified"] else "MISMATCH",
                "extraction_status": status,
                "extracted_file_count": file_count,
                "extracted_size_bytes": byte_count,
                "duration_seconds": round(time.monotonic() - started_at, 2),
                "details": detail,
            })

        extracted_files = [path for path in extracted_destination.rglob("*") if path.is_file() and path.name != ".extraction_complete.json"]
        image_files = [path for path in extracted_files if path.suffix.lower() in IMAGE_EXTENSIONS]
        formats = ";".join(sorted({path.suffix.lower().lstrip(".") for path in image_files})) or "NOT_REPORTED"
        write_csv(metadata_destination / "archive_checksums.csv", list(checksum_rows[0]) if checksum_rows else ["relative_path", "size_bytes", "source_sha256", "copied_sha256", "copy_status", "integrity_status"], checksum_rows)
        write_csv(metadata_destination / "extracted_inventory.csv", ["relative_path", "size_bytes"], [{"relative_path": str(path.relative_to(extracted_destination)).replace("\\", "/"), "size_bytes": path.stat().st_size} for path in extracted_files])
        (metadata_destination / "source_metadata.json").write_text(json.dumps({"dataset_id": dataset, "source_document": "SOURCE.md" if source_document.exists() else "NOT_REPORTED", "generated_utc": datetime.now(timezone.utc).isoformat(), "copy_root": str(downloads_destination)}, indent=2), encoding="utf-8")
        relevant_extractions = [row for row in extraction_rows if row["dataset_id"] == dataset]
        (destination_dataset / "EXTRACTION_REPORT.md").write_text("# Extraction Report\n\n" + "\n".join(f"- `{row['archive']}` — {row['extraction_status']}; {row['details']}" for row in relevant_extractions) + "\n", encoding="utf-8")
        (destination_dataset / "DATASET_NOTES.md").write_text(f"# Dataset Notes: {dataset}\n\n- Source evidence: `SOURCE.md` {'copied from the supplied source inbox.' if source_document.exists() else 'was not supplied.'}\n- Original source hierarchy is preserved beneath `downloads/` and `extracted/`.\n- Extracted images currently counted: {len(image_files)}.\n- Image formats: {formats}.\n- Labels, class counts, annotation formats, and quality limitations require source-specific validation; no labels or images were altered.\n", encoding="utf-8")
        inventory.append({"dataset_id": f"shared_{dataset}", "dataset_name": dataset, "category": "SHARED", "source_name": "See SOURCE.md" if source_document.exists() else "UNKNOWN", "source_url": "See SOURCE.md" if source_document.exists() else "UNKNOWN", "DOI": "NOT_REPORTED", "version": "NOT_REPORTED", "licence": "See SOURCE.md" if source_document.exists() else "UNKNOWN", "download_status": "COPIED_AND_VERIFIED", "archive_count": len(archive_rows), "archive_size_bytes": sum(row["destination"].stat().st_size for row in archive_rows), "archive_sha256": "See metadata/archive_checksums.csv", "archive_integrity_status": "MATCH" if all(row["verified"] for row in archive_rows) else "MISMATCH", "extraction_status": "SUCCESS" if relevant_extractions and all(row["extraction_status"] in {"SUCCESS", "SKIPPED_COMPLETED"} for row in relevant_extractions) else "PARTIAL_OR_FAILED", "extracted_file_count": len(extracted_files), "image_count": len(image_files), "image_formats": formats, "class_count": "NOT_REPORTED", "annotation_format": "NOT_REPORTED", "notes": "Original hierarchy preserved; see dataset reports.", "destination_path": str(destination_dataset.relative_to(args.destination)).replace("\\", "/")})

    write_csv(args.destination / "DATASET_INVENTORY.csv", ["dataset_id", "dataset_name", "category", "source_name", "source_url", "DOI", "version", "licence", "download_status", "archive_count", "archive_size_bytes", "archive_sha256", "archive_integrity_status", "extraction_status", "extracted_file_count", "image_count", "image_formats", "class_count", "annotation_format", "notes", "destination_path"], inventory)
    write_csv(args.destination / "metadata_shared_extraction_log.csv", ["dataset_id", "archive", "integrity_status", "extraction_status", "extracted_file_count", "extracted_size_bytes", "duration_seconds", "details"], extraction_rows)
    print(json.dumps({"started_utc": started, "finished_utc": datetime.now(timezone.utc).isoformat(), "datasets": len(inventory), "archives": len(extraction_rows)}, indent=2))


if __name__ == "__main__":
    main()
