from pathlib import Path

from PIL import Image

from training.chilli_data import CLASS_NAMES, build_chilli_manifest


def test_manifest_excludes_corrupt_and_cross_class_duplicates(tmp_path: Path) -> None:
    root, output = tmp_path / "raw", tmp_path / "out"
    shared = None
    for index, label in enumerate(CLASS_NAMES):
        folder = root / label; folder.mkdir(parents=True)
        for image_index in range(4):
            path = folder / f"{image_index}.jpg"
            Image.new("RGB", (8, 8), (index * 20, image_index * 30, 10)).save(path)
        if label == CLASS_NAMES[0]:
            shared = folder / "shared.jpg"; Image.new("RGB", (8, 8), "red").save(shared)
    assert shared is not None
    (root / CLASS_NAMES[1] / "shared.jpg").write_bytes(shared.read_bytes())
    (root / CLASS_NAMES[2] / "corrupt.jpg").write_bytes(b"not an image")
    result = build_chilli_manifest(root, output, seed=42)
    assert result["counts_by_split"]["train"] > 0
    manifest = (output / "chilli_ch001_original_manifest.csv").read_text(encoding="utf-8")
    assert "shared.jpg" not in manifest and "corrupt.jpg" not in manifest
