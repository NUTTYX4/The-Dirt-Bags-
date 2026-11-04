"""Print the local PyTorch/CUDA configuration required by CropScope training."""
from __future__ import annotations
import json
import torch

info = {"torch": torch.__version__, "torch_cuda": torch.version.cuda, "cuda_available": torch.cuda.is_available()}
if torch.cuda.is_available():
    properties = torch.cuda.get_device_properties(0)
    info.update({"gpu": properties.name, "vram_gib": round(properties.total_memory / 1024**3, 2), "cudnn": torch.backends.cudnn.version()})
print(json.dumps(info, indent=2))
if not torch.cuda.is_available():
    raise SystemExit("CUDA is unavailable. Install a CUDA-enabled PyTorch wheel and verify the NVIDIA driver with nvidia-smi; CPU training is disabled by default.")
