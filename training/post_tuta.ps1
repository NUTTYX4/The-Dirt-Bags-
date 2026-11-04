param([int]$TrainingPid)
Wait-Process -Id $TrainingPid
$run = 'training/outputs/tuta_binary_20261105'
$root = 'DATASETS/TOMATO/tuta_absoluta/extracted'
& .\.venv\Scripts\python.exe training\evaluate_tuta.py --run $run --root $root
$image = (Get-ChildItem $root -Recurse -File -Filter *.JPG | Select-Object -First 1).FullName
& .\.venv\Scripts\python.exe training\infer_classifier.py --run $run --image $image
& .\.venv\Scripts\python.exe training\evaluate_external_tomato.py --source 'DATASETS/SHARED/plantwild/extracted/plantwild/plantwild/images' --run 'training/outputs/tomato_plantvillage_20261105' --out 'training/outputs/tomato_plantvillage_20261105/external_plantwild'
