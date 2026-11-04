# CH-001 Chilli baseline: Kaggle runbook

This runbook trains only the six-class **original** CH-001 Chilli dataset.

## 1. Package and upload the input archive

From PowerShell at the repository root, create the Kaggle input archive without
altering the source images:

```powershell
Compress-Archive -LiteralPath 'DATASETS\CHILLI\chilli_leaf_disease\ch001_mendeley_v3\extracted\Chili Leaf Disease Original Dataset\Chili Leaf Disease Original Dataset' -DestinationPath '.\chilli-original-images.zip' -Force
kaggle config view
New-Item -ItemType Directory -Force .\kaggle_chilli_dataset | Out-Null
Copy-Item .\chilli-original-images.zip .\kaggle_chilli_dataset\chilli-original-images.zip
Copy-Item .\training\kaggle\chilli_classifier\dataset-metadata.json.template .\kaggle_chilli_dataset\dataset-metadata.json
kaggle datasets create -p .\kaggle_chilli_dataset
```

The archive contains only the original CH-001 class directories. For updates,
run:

```powershell
kaggle datasets version -p .\kaggle_chilli_dataset -m "CH-001 original images"
```

## 2. Push and run the private Tesla T4 kernel

```powershell
cd training\kaggle\chilli_classifier
kaggle kernels push -p .
kaggle kernels status ashray777/cropscope-chilli-classifier-baseline
```

For a pipeline check before full training, temporarily add `--smoke-test` to the
Kaggle script arguments, push, and inspect the output logs.

## 3. Download outputs

```powershell
kaggle kernels output ashray777/cropscope-chilli-classifier-baseline -p .\kaggle_outputs
```

Expected artifacts are under `cropscope_outputs/`: checkpoints, metrics,
metadata, and `export/chilli_mobilenetv3.onnx`. Do not commit those artifacts.
