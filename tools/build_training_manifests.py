"""Build a portable, no-copy CH-001 original Chilli training manifest."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from training.chilli_data import build_chilli_manifest

DEFAULT_DATASET = Path("DATASETS/CHILLI/chilli_leaf_disease/ch001_mendeley_v3/extracted/Chili Leaf Disease Original Dataset/Chili Leaf Disease Original Dataset")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=Path(os.environ.get("CROPSCOPE_DATASET_ROOT", DEFAULT_DATASET)))
    parser.add_argument("--output-dir", type=Path, default=Path(os.environ.get("CROPSCOPE_TRAINING_READY", "DATASETS/TRAINING_READY")))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--smoke-limit-per-class", type=int, default=None)
    args = parser.parse_args()
    print(json.dumps(build_chilli_manifest(args.dataset_root, args.output_dir, args.seed, args.smoke_limit_per_class), indent=2))


if __name__ == "__main__":
    main()
