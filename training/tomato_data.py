"""Preparation for the verified PlantVillage Tomato disease source only."""
from __future__ import annotations
import csv, hashlib, json, random
from collections import Counter, defaultdict
from pathlib import Path
from PIL import Image, UnidentifiedImageError

SOURCE_LABELS = {
    "Tomato___Bacterial_spot": "Bacterial spot", "Tomato___Early_blight": "Early blight",
    "Tomato___healthy": "Healthy", "Tomato___Late_blight": "Late blight",
    "Tomato___Leaf_Mold": "Leaf mold", "Tomato___Septoria_leaf_spot": "Septoria leaf spot",
    "Tomato___Target_Spot": "Target spot", "Tomato___Tomato_mosaic_virus": "Tomato mosaic virus",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "Tomato yellow leaf curl virus",
}
EXTS={".jpg",".jpeg",".png",".webp"}

def digest(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
    return h.hexdigest()

def okay(path):
    try:
        with Image.open(path) as im: im.verify()
        return True
    except (UnidentifiedImageError,OSError,ValueError): return False

def prepare(root:Path, output:Path, seed=42):
    root,output=root.resolve(),output.resolve(); output.mkdir(parents=True,exist_ok=True)
    labels=sorted(SOURCE_LABELS.values()); mapping={name:i for i,name in enumerate(labels)}; skipped=[]; candidates=[]
    for source,label in SOURCE_LABELS.items():
        folder=root/source
        if not folder.is_dir(): raise FileNotFoundError(folder)
        for path in sorted(folder.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in EXTS: continue
            rel=path.relative_to(root).as_posix()
            if not okay(path): skipped.append({"relative_path":rel,"reason":"unreadable_image"}); continue
            candidates.append({"dataset_id":"plantvillage_tomato","source_id":"plantvillage_color","relative_path":rel,"label":label,"class_index":mapping[label],"sha256":digest(path)})
    groups=defaultdict(list)
    for row in candidates: groups[row["sha256"]].append(row)
    rows=[]
    for h,group in groups.items():
        if len({r["label"] for r in group})>1: skipped.extend({"relative_path":r["relative_path"],"reason":"cross_class_exact_duplicate"} for r in group)
        else:
            rows.append(group[0]); skipped.extend({"relative_path":r["relative_path"],"reason":"within_class_exact_duplicate"} for r in group[1:])
    final=[]
    for label in labels:
        group=[r for r in rows if r["label"]==label]
        if len(group)<3: raise ValueError(f"insufficient {label}")
        random.Random(f"{seed}:{label}").shuffle(group); n=len(group); nv=max(1,round(n*.15)); nt=max(1,round(n*.15)); ntrain=n-nv-nt
        for i,row in enumerate(group): row["split"]="train" if i<ntrain else "validation" if i<ntrain+nv else "test"; final.append(row)
    fields=["dataset_id","source_id","relative_path","label","class_index","split","sha256"]
    with (output/"dataset_manifest.csv").open("w",newline="",encoding="utf-8") as f: w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(final)
    (output/"class_names.json").write_text(json.dumps(labels,indent=2)); (output/"dataset_summary.json").write_text(json.dumps({"source":"PlantVillage color / Tomato only","total":len(final),"counts":dict(Counter(r["label"] for r in final)),"splits":dict(Counter(r["split"] for r in final)),"skipped":skipped},indent=2))
    return final,labels
