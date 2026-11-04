"""Build a reproducible capped IP102 manifest while preserving official splits."""
from __future__ import annotations
import argparse,csv,json,random
from collections import Counter,defaultdict
from pathlib import Path
def rows(file,split):
 # Official split files use zero-based targets; classes.txt is displayed 1..102.
 return [(n,int(y),split) for n,y in (line.rsplit(maxsplit=1) for line in file.read_text().splitlines() if line.strip())]
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);p.add_argument('--out',required=True);p.add_argument('--cap',type=int,default=500);a=p.parse_args();root,out=Path(a.root),Path(a.out);out.mkdir(parents=True,exist_ok=True); names=[]
 for line in (root.parent.parent.parent/'downloads/google_drive_folder/Classification/classes.txt').read_text().splitlines(): names.append(line.split(maxsplit=1)[1].strip())
 data=rows(root/'train.txt','train')+rows(root/'val.txt','validation')+rows(root/'test.txt','test'); by=defaultdict(list)
 for x in data:
  if x[2]=='train':by[x[1]].append(x)
 rnd=random.Random(42); keep=[]
 for v in by.values():rnd.shuffle(v);keep+=v[:a.cap]
 keep += [x for x in data if x[2]!='train']; manifest=[]; missing=[]
 for n,i,s in keep:
  f=root/'images'/n
  if f.exists():manifest.append({'dataset_id':'ip102_v1_1','relative_path':'images/'+n,'label':names[i],'class_index':i,'split':s,'sha256':'NOT_COMPUTED_FAST_EXPERIMENT'})
  else:missing.append(n)
 with (out/'dataset_manifest.csv').open('w',newline='',encoding='utf8') as f:w=csv.DictWriter(f,manifest[0].keys());w.writeheader();w.writerows(manifest)
 (out/'class_names.json').write_text(json.dumps(names,indent=2));(out/'dataset_summary.json').write_text(json.dumps({'official_splits':True,'train_cap_per_class':a.cap,'counts':Counter(x['split'] for x in manifest),'missing_images':len(missing),'class_count':len(names)},indent=2,default=dict));print(len(manifest))
if __name__=='__main__':main()
