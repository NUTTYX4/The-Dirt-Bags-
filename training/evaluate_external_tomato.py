"""Screen PlantVillage Tomato model on confidently mapped PlantWild Tomato images."""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
import torch,torch.nn as nn
from PIL import Image
from sklearn.metrics import accuracy_score,classification_report,f1_score,confusion_matrix
from torchvision import transforms
from torchvision.models import mobilenet_v3_large
MAP={"tomato bacterial leaf spot":"Bacterial spot","tomato early blight":"Early blight","tomato late blight":"Late blight","tomato leaf mold":"Leaf mold","tomato mosaic virus":"Tomato mosaic virus","tomato septoria leaf spot":"Septoria leaf spot","tomato yellow leaf curl virus":"Tomato yellow leaf curl virus"}
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--run',required=True);p.add_argument('--out',required=True);a=p.parse_args(); src,run,out=Path(a.source),Path(a.run),Path(a.out);out.mkdir(parents=True,exist_ok=True)
 names=json.loads((run/'class_names.json').read_text()); idx={n:i for i,n in enumerate(names)}; rows=[]
 for d in src.iterdir():
  if d.is_dir() and d.name.lower() in MAP:
   for f in d.rglob('*'):
    if f.suffix.lower() in {'.jpg','.jpeg','.png','.webp'}: rows.append((f,MAP[d.name.lower()]))
 with (out/'manifest.csv').open('w',newline='',encoding='utf8') as f: w=csv.writer(f);w.writerow(['path','label']);w.writerows((str(x),y) for x,y in rows)
 st=torch.load(run/'best_model.pth',map_location='cuda',weights_only=False);m=mobilenet_v3_large(weights=None);m.classifier[3]=nn.Linear(m.classifier[3].in_features,len(names));m.load_state_dict(st['model']);m.cuda().eval();tf=transforms.Compose([transforms.Resize(256),transforms.CenterCrop(224),transforms.ToTensor(),transforms.Normalize([.485,.456,.406],[.229,.224,.225])]); y=[];z=[]
 with torch.inference_mode():
  for f,label in rows:
   with Image.open(f) as im: q=m(tf(im.convert('RGB')).unsqueeze(0).cuda()).argmax(1).item()
   y.append(idx[label]);z.append(q)
 result={'source':'PlantWild','compatible_images':len(rows),'excluded_classes':['tomato leaf'],'accuracy':accuracy_score(y,z),'macro_f1':f1_score(y,z,average='macro'),'per_class':classification_report(y,z,labels=list(range(len(names))),target_names=names,output_dict=True,zero_division=0)}
 (out/'evaluation_metrics.json').write_text(json.dumps(result,indent=2)); (out/'classification_report.txt').write_text(classification_report(y,z,labels=list(range(len(names))),target_names=names,zero_division=0)); (out/'confusion_matrix.json').write_text(json.dumps(confusion_matrix(y,z).tolist()));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
