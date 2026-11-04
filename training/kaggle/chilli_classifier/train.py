"""Kaggle Tesla T4 baseline: MobileNetV3-Large for original CH-001 Chilli data."""
from __future__ import annotations

import argparse, csv, hashlib, json, os, random, shutil, subprocess, sys, time, zipfile
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
import yaml
from PIL import Image, UnidentifiedImageError
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score, precision_recall_fscore_support
from torch.optim import AdamW
from torch.optim.lr_scheduler import ReduceLROnPlateau
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms
from torchvision.models import MobileNet_V3_Large_Weights, mobilenet_v3_large

CLASSES = ["Bacterial Spot", "Cercospora Leaf Spot", "Curl Virus", "Healthy Leaf", "Nutrition Deficiency", "White spot"]
EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}

def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""): h.update(block)
    return h.hexdigest()

def safe_extract(zip_path, output):
    output = output.resolve()
    with zipfile.ZipFile(zip_path) as z:
        if z.testzip(): raise RuntimeError(f"Archive CRC failed: {z.testzip()}")
        for item in z.infolist():
            dest = (output / item.filename).resolve()
            if not str(dest).startswith(str(output) + os.sep) and dest != output: raise RuntimeError(f"Unsafe path: {item.filename}")
            if (item.external_attr >> 16) & 0o170000 == 0o120000: raise RuntimeError(f"Symlink entry rejected: {item.filename}")
        z.extractall(output)

def find_dataset_root(root):
    matches = []
    for path in root.rglob("*"):
        if path.is_dir() and sorted(x.name for x in path.iterdir() if x.is_dir()) == sorted(CLASSES): matches.append(path)
    if len(matches) != 1: raise RuntimeError(f"Expected one six-class CH-001 root; found {matches}")
    return matches[0]

def valid_image(path):
    try:
        with Image.open(path) as image: image.verify()
        with Image.open(path) as image: image.load()
        return True
    except (UnidentifiedImageError, OSError, ValueError): return False

def prepare_manifest(root, output, seed=42):
    output.mkdir(parents=True, exist_ok=True); rows=[]; skipped=[]; seen=defaultdict(list)
    for idx, label in enumerate(CLASSES):
        for path in sorted((root / label).rglob("*")):
            if not path.is_file() or path.name.startswith(".") or path.suffix.lower() not in EXTS:
                if path.is_file(): skipped.append({"path": str(path.relative_to(root)), "reason": "non_image_or_metadata"})
                continue
            if not valid_image(path): skipped.append({"path": str(path.relative_to(root)), "reason": "unreadable_image"}); continue
            digest=sha(path); row={"dataset_id":"chilli_ch001_original_v3","relative_path":path.relative_to(root).as_posix(),"label":label,"class_index":idx,"sha256":digest}; rows.append(row); seen[digest].append(row)
    allowed=[]
    for digest, group in seen.items():
        labels={x["label"] for x in group}
        if len(labels)>1:
            skipped.extend({"path":x["relative_path"],"reason":"cross_class_exact_duplicate"} for x in group); continue
        allowed.append(sorted(group,key=lambda x:x["relative_path"])[0])
        skipped.extend({"path":x["relative_path"],"reason":"within_class_exact_duplicate"} for x in sorted(group,key=lambda x:x["relative_path"])[1:])
    out=[]
    for label in CLASSES:
        group=[x for x in allowed if x["label"]==label]
        if len(group)<3: raise RuntimeError(f"Insufficient usable images for {label}: {len(group)}")
        random.Random(f"{seed}:{label}").shuffle(group); n=len(group); nv=max(1,round(n*.15)); nt=max(1,round(n*.15)); ntrain=n-nv-nt
        for i,row in enumerate(group): row["split"]="train" if i<ntrain else "validation" if i<ntrain+nv else "test"; out.append(row)
    manifest=output/"chilli_ch001_original_manifest.csv"
    with manifest.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=["dataset_id","relative_path","label","class_index","split","sha256"]); w.writeheader(); w.writerows(out)
    (output/"class_to_idx.json").write_text(json.dumps({x:i for i,x in enumerate(CLASSES)},indent=2))
    (output/"chilli_data_quality_report.json").write_text(json.dumps({"included":len(out),"skipped":skipped,"cross_class_hashes":sum(len({x['label'] for x in g})>1 for g in seen.values())},indent=2))
    return manifest, out

class ManifestDataset(Dataset):
    def __init__(self, root, rows, transform): self.root,self.rows,self.transform=root,rows,transform
    def __len__(self): return len(self.rows)
    def __getitem__(self,i):
        row=self.rows[i]
        with Image.open(self.root/row["relative_path"]) as image: image=image.convert("RGB")
        return self.transform(image), int(row["class_index"])

def loader(root, rows, transform, cfg, shuffle):
    workers=int(cfg["num_workers"])
    return DataLoader(ManifestDataset(root,rows,transform), batch_size=int(cfg["batch_size"]), shuffle=shuffle, num_workers=workers, pin_memory=bool(cfg["pin_memory"]), persistent_workers=workers>0)

def run_epoch(model, data, optimizer, scaler, criterion, device, training, max_batches=None):
    model.train(training); losses=[]; actual=[]; predicted=[]
    for step,(images,labels) in enumerate(data):
        if max_batches and step>=max_batches: break
        images,labels=images.to(device,non_blocking=True),labels.to(device,non_blocking=True)
        if training: optimizer.zero_grad(set_to_none=True)
        with torch.autocast(device_type="cuda", dtype=torch.float16, enabled=device.type=="cuda"):
            logits=model(images); loss=criterion(logits,labels)
        if training: scaler.scale(loss).backward(); scaler.step(optimizer); scaler.update()
        losses.append(loss.item()); actual.extend(labels.cpu().tolist()); predicted.extend(logits.argmax(1).detach().cpu().tolist())
    return float(np.mean(losses)), accuracy_score(actual,predicted), f1_score(actual,predicted,average="macro",zero_division=0), actual,predicted

def main():
    p=argparse.ArgumentParser(); p.add_argument("--config",default=str(Path(__file__).with_name("chilli_ch001.yaml"))); p.add_argument("--resume"); p.add_argument("--smoke-test",action="store_true"); p.add_argument("--batch-size",type=int); args=p.parse_args()
    cfg=yaml.safe_load(Path(args.config).read_text());
    if args.batch_size: cfg["batch_size"]=args.batch_size
    random.seed(cfg["random_seed"]); np.random.seed(cfg["random_seed"]); torch.manual_seed(cfg["random_seed"]); torch.backends.cudnn.benchmark=True
    output=Path("/kaggle/working/cropscope_outputs"); checkpoints=output/"checkpoints"; metrics=output/"metrics"; metadata=output/"metadata"; export=output/"export"
    for d in (checkpoints,metrics,metadata,export): d.mkdir(parents=True,exist_ok=True)
    print(json.dumps({"torch":torch.__version__,"cuda":torch.cuda.is_available(),"gpu":torch.cuda.get_device_name(0) if torch.cuda.is_available() else None},indent=2))
    if not torch.cuda.is_available(): raise RuntimeError("Kaggle GPU is unavailable; enable Tesla T4 accelerator.")
    archive=next(Path("/kaggle/input").rglob("chilli-original-images.zip"),None)
    if archive is None: raise FileNotFoundError("chilli-original-images.zip not found under /kaggle/input")
    data=Path("/kaggle/working/data"); marker=data/".extracted"
    if not marker.exists():
        if shutil.disk_usage("/kaggle/working").free < archive.stat().st_size*2: raise RuntimeError("Insufficient Kaggle working disk space for extraction.")
        data.mkdir(parents=True,exist_ok=True); safe_extract(archive,data); marker.write_text("ok")
    root=find_dataset_root(data); manifest,rows=prepare_manifest(root,metadata,cfg["random_seed"])
    (metadata/"training_config.json").write_text(json.dumps(cfg,indent=2)); (metadata/"environment.json").write_text(json.dumps({"torch":torch.__version__,"cuda":torch.version.cuda,"gpu":torch.cuda.get_device_name(0)},indent=2)); (metadata/"dataset_manifest_summary.json").write_text(json.dumps(dict(Counter(x["split"] for x in rows)),indent=2))
    normal=transforms.Normalize([.485,.456,.406],[.229,.224,.225]); train_tf=transforms.Compose([transforms.RandomResizedCrop(cfg["image_size"],scale=(.8,1.0)),transforms.RandomHorizontalFlip(),transforms.RandomRotation(10),transforms.ColorJitter(.15,.15,.1,.05),transforms.ToTensor(),normal]); eval_tf=transforms.Compose([transforms.Resize(256),transforms.CenterCrop(cfg["image_size"]),transforms.ToTensor(),normal])
    by={split:[x for x in rows if x["split"]==split] for split in ("train","validation","test")}; print({k:len(v) for k,v in by.items()}); print({split:dict(Counter(x["label"] for x in values)) for split,values in by.items()})
    train=loader(root,by["train"],train_tf,cfg,True); valid=loader(root,by["validation"],eval_tf,cfg,False); test=loader(root,by["test"],eval_tf,cfg,False)
    device=torch.device("cuda"); model=mobilenet_v3_large(weights=MobileNet_V3_Large_Weights.IMAGENET1K_V2 if cfg["pretrained"] else None); model.classifier[3]=nn.Linear(model.classifier[3].in_features,len(CLASSES)); model=model.to(device)
    counts=Counter(x["class_index"] for x in by["train"]); weights=torch.tensor([len(by["train"])/(len(CLASSES)*counts[i]) for i in range(len(CLASSES))],device=device); criterion=nn.CrossEntropyLoss(weight=weights); optimizer=AdamW(model.parameters(),lr=float(cfg["learning_rate"]),weight_decay=float(cfg["weight_decay"])); scheduler=ReduceLROnPlateau(optimizer,mode="max",patience=2,factor=.3); scaler=torch.amp.GradScaler("cuda"); start=0; best=-1; patience=0; history=[]
    if args.resume:
        state=torch.load(args.resume,map_location=device); model.load_state_dict(state["model"]); optimizer.load_state_dict(state["optimizer"]); scheduler.load_state_dict(state["scheduler"]); start=state["epoch"]+1; best=state["best_f1"]
    for epoch in range(start,int(cfg["epochs"])):
        if epoch < int(cfg["warmup_epochs"]):
            for name,param in model.features.named_parameters(): param.requires_grad=False
        else:
            for param in model.parameters(): param.requires_grad=True
        tl,ta,tf,_,_=run_epoch(model,train,optimizer,scaler,criterion,device,True,2 if args.smoke_test else None); vl,va,vf,_,_=run_epoch(model,valid,optimizer,scaler,criterion,device,False,2 if args.smoke_test else None); scheduler.step(vf); item={"epoch":epoch+1,"train_loss":tl,"train_accuracy":ta,"train_macro_f1":tf,"validation_loss":vl,"validation_accuracy":va,"validation_macro_f1":vf}; history.append(item); print(item)
        state={"epoch":epoch,"model":model.state_dict(),"optimizer":optimizer.state_dict(),"scheduler":scheduler.state_dict(),"best_f1":best,"config":cfg}; torch.save(state,checkpoints/"last_checkpoint.pth")
        if vf>best: best=vf; patience=0; state["best_f1"]=best; torch.save(state,checkpoints/"best_model.pth")
        else: patience+=1
        if args.smoke_test or patience>=int(cfg["early_stopping_patience"]): break
    with (metrics/"training_history.csv").open("w",newline="") as f: w=csv.DictWriter(f,fieldnames=history[0]); w.writeheader(); w.writerows(history)
    state=torch.load(checkpoints/"best_model.pth",map_location=device); model.load_state_dict(state["model"]); _,acc,f1,y_true,y_pred=run_epoch(model,test,optimizer,scaler,criterion,device,False); prec,rec,fs,_=precision_recall_fscore_support(y_true,y_pred,labels=list(range(6)),zero_division=0); report=classification_report(y_true,y_pred,target_names=CLASSES,output_dict=True,zero_division=0); result={"accuracy":acc,"macro_precision":float(np.mean(prec)),"macro_recall":float(np.mean(rec)),"macro_f1":f1,"per_class_precision":dict(zip(CLASSES,prec.tolist())),"per_class_recall":dict(zip(CLASSES,rec.tolist())),"per_class_f1":dict(zip(CLASSES,fs.tolist())),"report":report}; (metrics/"classification_report.json").write_text(json.dumps(result,indent=2)); (metrics/"metrics.json").write_text(json.dumps(result,indent=2)); cm=confusion_matrix(y_true,y_pred); plt.figure(figsize=(8,7)); plt.imshow(cm,cmap="Blues"); plt.xticks(range(6),CLASSES,rotation=45,ha="right"); plt.yticks(range(6),CLASSES); plt.colorbar(); plt.tight_layout(); plt.savefig(metrics/"confusion_matrix.png",dpi=160)
    model.eval(); sample=torch.randn(1,3,cfg["image_size"],cfg["image_size"],device=device); torch.onnx.export(model,sample,export/"chilli_mobilenetv3.onnx",input_names=["image"],output_names=["logits"],opset_version=17)

if __name__=="__main__":
    try:
        main()
    except torch.OutOfMemoryError:
        current = 64
        if "--batch-size" in sys.argv:
            current = int(sys.argv[sys.argv.index("--batch-size") + 1])
        retry = 32 if current > 32 else 16 if current > 16 else None
        if retry is None:
            raise
        print(f"CUDA OOM at batch size {current}; retrying from scratch with batch size {retry}.", flush=True)
        torch.cuda.empty_cache()
        raise SystemExit(subprocess.call([sys.executable, __file__, *sys.argv[1:], "--batch-size", str(retry)]))
