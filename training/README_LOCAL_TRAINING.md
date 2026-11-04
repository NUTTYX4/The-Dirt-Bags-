# Local RTX 3050 Chilli baseline

Activate the environment with `./.venv/Scripts/Activate.ps1`, then run
`python training/check_local_gpu.py` and
`python training/train_local.py --config training/configs/chilli_baseline.yaml`.

The default batch size is 16 for the 6 GB RTX 3050. If CUDA OOM occurs, retry
with `--batch-size 8`, then `--batch-size 4`. Use `--smoke-test` first; use
`--resume training/outputs/chilli_baseline/last_model.pth` to resume.
