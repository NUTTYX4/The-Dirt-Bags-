"""Prepare the documented Tuta image-level binary dataset without touching raw files."""
from __future__ import annotations
import argparse,csv,hashlib,json,random
from collections import Counter,defaultdict
from pathlib import Path
from PIL import Image,UnidentifiedImageError

CLASS_NAMES=["Healthy","Tuta absoluta affected"]
EXT={".jpg",".jpeg",".png",".webp"}
def sha(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def split(items,seed=42):
 r=random.Random(seed); r.shuffle(items); n=len(items); a=round(n*.70); b=round(n*.15); return ["train"]*a+["validation"]*b+["test"]*(n-a-b)
def build(root:Path,csv_path:Path,out:Path):
 out.mkdir(parents=True,exist_ok=True); labels={r["FileName"]:r["Label"] for r in csv.DictReader(csv_path.open(encoding="utf-8-sig"))}; files={p.name:p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in EXT and "__MACOSX" not in p.parts}
 rows=[]; skipped=[]; hashes=defaultdict(list)
 for name,label in labels.items():
  p=files.get(name)
  if not p: skipped.append({"file":name,"reason":"missing"}); continue
  try:
   with Image.open(p) as im: im.verify()
  except (UnidentifiedImageError,OSError): skipped.append({"file":name,"reason":"corrupt"}); continue
  hashes[sha(p)].append((p,label))
 for h,group in hashes.items():
  labs={x[1] for x in group}
  if len(labs)>1:
   for p,_ in group: skipped.append({"file":p.name,"reason":"conflicting_exact_duplicate"})
  else:
   p,label=group[0]; rows.append({"dataset_id":"tuta_absoluta_image_labels","relative_path":p.relative_to(root).as_posix(),"label":CLASS_NAMES[int(label)-1],"class_index":str(int(label)-1),"sha256":h})
 by=defaultdict(list)
 for row in rows: by[row["class_index"]].append(row)
 for group in by.values():
  for row,s in zip(group,split(group)): row["split"]=s
 rows.sort(key=lambda x:(x["split"],x["relative_path"]))
 fields=["dataset_id","relative_path","label","class_index","split","sha256"]
 with (out/"dataset_manifest.csv").open("w",newline="",encoding="utf-8") as f: w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
 with (out/"skipped_files.csv").open("w",newline="",encoding="utf-8") as f: w=csv.DictWriter(f,["file","reason"]);w.writeheader();w.writerows(skipped)
 summary={"source_csv_rows":len(labels),"raw_images_found":len(files),"usable_images":len(rows),"skipped":len(skipped),"duplicate_hash_groups":sum(len(g)>1 for g in hashes.values()),"class_counts":Counter(r["label"] for r in rows),"split_counts":{s:Counter(r["label"] for r in rows if r["split"]==s) for s in ("train","validation","test")},"grouping":"No plant/capture ID exists in CSV or filenames; deterministic stratified image-level split used. Sequential/capture leakage cannot be ruled out."}
 (out/"class_names.json").write_text(json.dumps(CLASS_NAMES,indent=2));(out/"dataset_summary.json").write_text(json.dumps(summary,indent=2,default=dict));(out/"dataset_audit.json").write_text(json.dumps(summary,indent=2,default=dict)); return summary
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--root",required=True);p.add_argument("--labels",required=True);p.add_argument("--out",required=True);a=p.parse_args();print(json.dumps(build(Path(a.root),Path(a.labels),Path(a.out)),indent=2,default=dict))
