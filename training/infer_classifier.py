"""Run inference for a completed MobileNetV3 CropScope classifier."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms
from torchvision.models import mobilenet_v3_large

def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--run",required=True); p.add_argument("--image",required=True); p.add_argument("--top-k",type=int,default=3); args=p.parse_args()
    run=Path(args.run); state=torch.load(run/"best_model.pth",map_location="cpu",weights_only=False); names=json.loads((run/"class_names.json").read_text()); size=int(state["config"].get("image_size",224))
    model=mobilenet_v3_large(weights=None); model.classifier[3]=nn.Linear(model.classifier[3].in_features,len(names)); model.load_state_dict(state["model"]); model.eval()
    tf=transforms.Compose([transforms.Resize(256),transforms.CenterCrop(size),transforms.ToTensor(),transforms.Normalize([.485,.456,.406],[.229,.224,.225])])
    with Image.open(args.image) as im, torch.inference_mode(): probs=torch.softmax(model(tf(im.convert("RGB")).unsqueeze(0))[0],0)
    for i in torch.topk(probs,min(args.top_k,len(names))).indices.tolist(): print(f"{names[i]}\t{probs[i].item():.4f}")

if __name__ == "__main__": main()
