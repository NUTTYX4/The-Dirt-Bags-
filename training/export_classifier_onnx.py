"""Export a completed CropScope MobileNetV3 classifier without altering its run."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import torch
import torch.nn as nn
from torchvision.models import mobilenet_v3_large

def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--run", required=True); args=p.parse_args()
    run=Path(args.run); names=json.loads((run/"class_names.json").read_text())
    state=torch.load(run/"best_model.pth",map_location="cpu",weights_only=False)
    model=mobilenet_v3_large(weights=None); model.classifier[3]=nn.Linear(model.classifier[3].in_features,len(names)); model.load_state_dict(state["model"]); model.eval()
    size=int(state["config"].get("image_size",224)); sample=torch.randn(1,3,size,size)
    target=run/"model.onnx"
    try:
        # Legacy exporter avoids Windows console Unicode emitted by the newer exporter.
        torch.onnx.export(model,sample,target,input_names=["image"],output_names=["logits"],dynamic_axes={"image":{0:"batch"},"logits":{0:"batch"}},opset_version=17,dynamo=False)
        print(f"Exported {target}")
    except ModuleNotFoundError as exc:
        print(f"ONNX export pending (missing optional dependency): {exc}")

if __name__ == "__main__": main()
