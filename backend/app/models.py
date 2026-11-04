import json,time
from pathlib import Path
import numpy as np,yaml,onnxruntime as ort
from PIL import Image
class Registry:
 def __init__(self):
  self.items={x['id']:x for x in yaml.safe_load(Path('/app/model_registry.yaml').read_text())['models']};self.sessions={}
 def details(self):
  return [{**x,'ready':Path(x['artifact']).exists() and Path(x['metadata_dir'],'class_names.json').exists(),'supported_formats':['image/jpeg','image/png','image/webp']} for x in self.items.values()]
 def predict(self,model_id,data,top_k):
  x=self.items.get(model_id)
  if not x or not Path(x['artifact']).exists():raise ValueError('Requested model is not ready')
  im=Image.open(data).convert('RGB'); im.thumbnail((256,256)); canvas=Image.new('RGB',(256,256),(0,0,0));canvas.paste(im,((256-im.width)//2,(256-im.height)//2)); a=np.asarray(canvas.crop((16,16,240,240)),dtype=np.float32).transpose(2,0,1)/255.;a=(a-np.array([.485,.456,.406])[:,None,None])/np.array([.229,.224,.225])[:,None,None]
  s=self.sessions.setdefault(model_id,ort.InferenceSession(x['artifact'],providers=['CPUExecutionProvider']));t=time.perf_counter(); logits=s.run(None,{s.get_inputs()[0].name:a[None].astype(np.float32)})[0][0]; p=np.exp(logits-logits.max());p/=p.sum(); names=json.loads(Path(x['metadata_dir'],'class_names.json').read_text()); ids=np.argsort(p)[::-1][:max(1,min(top_k,len(names)))];return {'model_id':model_id,'model_version':x['version'],'predicted_label':names[int(ids[0])],'confidence':float(p[ids[0]]),'top_k':[{'label':names[int(i)],'confidence':float(p[i])} for i in ids],'inference_time_ms':round((time.perf_counter()-t)*1000,2)}
registry=Registry()
