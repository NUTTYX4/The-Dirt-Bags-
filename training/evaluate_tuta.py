"""Evaluate the saved Tuta classifier on its immutable manifest test partition."""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
import torch,torch.nn as nn
from PIL import Image
from sklearn.metrics import accuracy_score,classification_report,confusion_matrix,precision_recall_fscore_support
from torchvision import transforms
from torchvision.models import mobilenet_v3_large
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--root',required=True);a=p.parse_args();run,root=Path(a.run),Path(a.root); names=json.loads((run/'class_names.json').read_text()); rows=[r for r in csv.DictReader((run/'dataset_manifest.csv').open()) if r['split']=='test']; st=torch.load(run/'best_model.pth',map_location='cuda',weights_only=False);m=mobilenet_v3_large(weights=None);m.classifier[3]=nn.Linear(m.classifier[3].in_features,2);m.load_state_dict(st['model']);m.cuda().eval();tf=transforms.Compose([transforms.Resize(256),transforms.CenterCrop(224),transforms.ToTensor(),transforms.Normalize([.485,.456,.406],[.229,.224,.225])]); y=[];z=[];out=[]
 with torch.inference_mode():
  for r in rows:
   with Image.open(root/r['relative_path']) as im: q=m(tf(im.convert('RGB')).unsqueeze(0).cuda()).argmax(1).item()
   y.append(int(r['class_index']));z.append(q);out.append({'relative_path':r['relative_path'],'actual':names[int(r['class_index'])],'predicted':names[q],'false_negative':str(int(r['class_index'])==1 and q==0)})
 cm=confusion_matrix(y,z,labels=[0,1]); pr,re,f1,_=precision_recall_fscore_support(y,z,labels=[0,1],zero_division=0); result={'accuracy':accuracy_score(y,z),'macro_f1':float(f1.mean()),'healthy_specificity':float(re[0]),'tuta_precision':float(pr[1]),'tuta_recall':float(re[1]),'tuta_false_negatives':int(cm[1,0]),'confusion_matrix':cm.tolist(),'per_class':classification_report(y,z,target_names=names,output_dict=True,zero_division=0)}
 with (run/'test_predictions.csv').open('w',newline='',encoding='utf8') as f:w=csv.DictWriter(f,out[0]);w.writeheader();w.writerows(out)
 (run/'evaluation_metrics.json').write_text(json.dumps(result,indent=2));(run/'classification_report.txt').write_text(classification_report(y,z,target_names=names,zero_division=0));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
