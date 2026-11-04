"""Local Windows RTX training entry point for the CH-001 original Chilli baseline."""
from __future__ import annotations
import argparse, csv, json, random, shutil
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
import yaml
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_recall_fscore_support
from torch.optim import AdamW
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import MobileNet_V3_Large_Weights, mobilenet_v3_large

from chilli_data import CLASS_NAMES, build_chilli_manifest

NORMALIZE = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])

class ChilliManifestDataset(Dataset):
    def __init__(self, root: Path, rows: list[dict[str, str]], transform): self.root, self.rows, self.transform = root, rows, transform
    def __len__(self): return len(self.rows)
    def __getitem__(self, index):
        from PIL import Image
        row = self.rows[index]
        with Image.open(self.root / row["relative_path"]) as image: image = image.convert("RGB")
        return self.transform(image), int(row["class_index"])

def loader(root, rows, transform, config, shuffle):
    workers = int(config["num_workers"])
    return DataLoader(ChilliManifestDataset(root, rows, transform), batch_size=int(config["batch_size"]), shuffle=shuffle, num_workers=workers, pin_memory=bool(config["pin_memory"]), persistent_workers=workers > 0)

def epoch(model, data, optimizer, scaler, criterion, device, training, limit=None):
    model.train(training); losses=[]; actual=[]; predicted=[]
    for step, (images, labels) in enumerate(data):
        if limit and step >= limit: break
        images, labels = images.to(device, non_blocking=True), labels.to(device, non_blocking=True)
        if training: optimizer.zero_grad(set_to_none=True)
        with torch.autocast("cuda", dtype=torch.float16, enabled=device.type == "cuda"):
            logits = model(images); loss = criterion(logits, labels)
        if training: scaler.scale(loss).backward(); scaler.step(optimizer); scaler.update()
        losses.append(loss.item()); actual.extend(labels.cpu().tolist()); predicted.extend(logits.detach().argmax(1).cpu().tolist())
    return float(np.mean(losses)), accuracy_score(actual, predicted), f1_score(actual, predicted, average="macro", zero_division=0), actual, predicted

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--config", default="training/configs/chilli_baseline.yaml"); parser.add_argument("--resume"); parser.add_argument("--smoke-test", action="store_true"); parser.add_argument("--cpu", action="store_true"); parser.add_argument("--batch-size", type=int); args=parser.parse_args()
    config=yaml.safe_load(Path(args.config).read_text(encoding="utf-8"));
    if args.batch_size: config["batch_size"]=args.batch_size
    root=Path(config["dataset_root"]).resolve(); output=Path(config["output_dir"]).resolve(); output.mkdir(parents=True, exist_ok=True)
    if not args.cpu and not torch.cuda.is_available(): raise RuntimeError("CUDA unavailable. Run python training/check_local_gpu.py; use --cpu only for debugging.")
    device=torch.device("cpu" if args.cpu else "cuda"); random.seed(config["random_seed"]); np.random.seed(config["random_seed"]); torch.manual_seed(config["random_seed"])
    if device.type == "cuda": torch.backends.cudnn.benchmark=True; print(f"GPU: {torch.cuda.get_device_name(0)} | VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GiB")
    print(f"PyTorch: {torch.__version__}; CUDA: {torch.version.cuda}; device: {device}")
    if config.get("prepare_chilli", False):
        build_chilli_manifest(root, output, int(config["random_seed"])); manifest=output / "chilli_ch001_original_manifest.csv"; class_names=CLASS_NAMES
    else:
        manifest=Path(config["manifest_path"]).resolve(); class_names=json.loads(Path(config["class_names_path"]).resolve().read_text())
    rows=list(csv.DictReader(manifest.open(encoding="utf-8"))); by={split:[r for r in rows if r["split"]==split] for split in ("train","validation","test")}; print({k:len(v) for k,v in by.items()}); print({k:dict(Counter(r["label"] for r in v)) for k,v in by.items()})
    train_tf=transforms.Compose([transforms.RandomResizedCrop(config["image_size"], scale=(.8,1.0)), transforms.RandomHorizontalFlip(), transforms.RandomRotation(10), transforms.ColorJitter(.15,.15,.1,.05), transforms.ToTensor(), NORMALIZE]); eval_tf=transforms.Compose([transforms.Resize(256), transforms.CenterCrop(config["image_size"]), transforms.ToTensor(), NORMALIZE])
    train, valid, test = loader(root,by["train"],train_tf,config,True), loader(root,by["validation"],eval_tf,config,False), loader(root,by["test"],eval_tf,config,False)
    model=mobilenet_v3_large(weights=MobileNet_V3_Large_Weights.IMAGENET1K_V2 if config["pretrained"] else None); model.classifier[3]=nn.Linear(model.classifier[3].in_features,len(class_names)); model=model.to(device)
    counts=Counter(int(r["class_index"]) for r in by["train"]); weights=torch.tensor([len(by["train"])/(len(class_names)*counts[i]) if counts[i] else 0.0 for i in range(len(class_names))], device=device); criterion=nn.CrossEntropyLoss(weight=weights); optimizer=AdamW(model.parameters(),lr=float(config["learning_rate"]),weight_decay=float(config["weight_decay"])); scheduler=ReduceLROnPlateau(optimizer,mode="max",patience=2,factor=.3); scaler=torch.amp.GradScaler("cuda",enabled=device.type=="cuda" and config["mixed_precision"]); checkpoints=output; best=-1.; start=0; patience=0; history=[]
    if args.resume:
        state=torch.load(args.resume,map_location=device); model.load_state_dict(state["model"]); optimizer.load_state_dict(state["optimizer"]); scheduler.load_state_dict(state["scheduler"]); start=state["epoch"]+1; best=state["best_f1"]
    for ep in range(start, int(config["epochs"])):
        for param in model.features.parameters(): param.requires_grad = ep >= int(config["warmup_epochs"])
        tl,ta,tf,_,_=epoch(model,train,optimizer,scaler,criterion,device,True,2 if args.smoke_test else None); vl,va,vf,_,_=epoch(model,valid,optimizer,scaler,criterion,device,False,2 if args.smoke_test else None); scheduler.step(vf); item={"epoch":ep+1,"train_loss":tl,"train_accuracy":ta,"train_macro_f1":tf,"validation_loss":vl,"validation_accuracy":va,"validation_macro_f1":vf}; history.append(item); print(item); state={"epoch":ep,"model":model.state_dict(),"optimizer":optimizer.state_dict(),"scheduler":scheduler.state_dict(),"best_f1":best,"config":config}; torch.save(state,checkpoints/"last_model.pth")
        if vf>best: best=vf; patience=0; state["best_f1"]=best; torch.save(state,checkpoints/"best_model.pth")
        else: patience+=1
        if args.smoke_test or patience>=int(config["early_stopping_patience"]): break
    with (output/"training_metrics.csv").open("w",newline="") as file: writer=csv.DictWriter(file,fieldnames=history[0]); writer.writeheader(); writer.writerows(history)
    state=torch.load(checkpoints/"best_model.pth",map_location=device); model.load_state_dict(state["model"]); _,accuracy,macro_f1,y,pred=epoch(model,test,optimizer,scaler,criterion,device,False); precision,recall,f1,_=precision_recall_fscore_support(y,pred,labels=list(range(len(class_names))),zero_division=0); result={"accuracy":accuracy,"macro_precision":float(np.mean(precision)),"macro_recall":float(np.mean(recall)),"macro_f1":macro_f1,"per_class":classification_report(y,pred,target_names=class_names,output_dict=True,zero_division=0)}; (output/"evaluation_metrics.json").write_text(json.dumps(result,indent=2)); (output/"classification_report.txt").write_text(classification_report(y,pred,target_names=class_names,zero_division=0)); cm=confusion_matrix(y,pred); plt.figure(figsize=(8,7)); plt.imshow(cm,cmap="Blues"); plt.xticks(range(len(class_names)),class_names,rotation=45,ha="right"); plt.yticks(range(len(class_names)),class_names); plt.colorbar(); plt.tight_layout(); plt.savefig(output/"confusion_matrix.png",dpi=160); plt.close(); plt.figure(); plt.plot([x["epoch"] for x in history],[x["train_loss"] for x in history],label="train"); plt.plot([x["epoch"] for x in history],[x["validation_loss"] for x in history],label="validation"); plt.legend(); plt.savefig(output/"training_curves.png",dpi=160); plt.close(); (output/"class_names.json").write_text(json.dumps(class_names,indent=2)); (output/"model_metadata.json").write_text(json.dumps({"architecture":"mobilenet_v3_large","image_size":config["image_size"],"normalization":"ImageNet mean/std","checkpoint":"best_model.pth","config":config},indent=2))

if __name__ == "__main__": main()
