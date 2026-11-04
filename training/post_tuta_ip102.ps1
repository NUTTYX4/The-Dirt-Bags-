param([int]$PostTutaPid)
Wait-Process -Id $PostTutaPid
& .\.venv\Scripts\python.exe training\ip102_data.py --root 'DATASETS/SHARED/ip102/extracted/ip102_v1.1/ip102_v1.1' --out 'training/outputs/ip102_pest_fast_20261105' --cap 500
& .\.venv\Scripts\python.exe training\train_local.py --config training\configs\ip102_pest_fast.yaml
