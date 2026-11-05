"""Small live acceptance test. Run after `docker compose up -d` from backend/."""
from __future__ import annotations
import json,mimetypes,sys,uuid
from pathlib import Path
from urllib.request import Request,urlopen
BASE='http://127.0.0.1:8000'; ASSETS=Path(__file__).parents[1]/'test_assets'; results={}
def get(path):
 with urlopen(BASE+path,timeout=30) as r:return r.status,json.loads(r.read())
def post(path,fields,filename=None,data=None):
 boundary='----crop'+uuid.uuid4().hex; body=[]
 for k,v in fields.items():body += [f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()]
 if filename: body += [f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{filename}"\r\nContent-Type: {mimetypes.guess_type(filename)[0] or "application/octet-stream"}\r\n\r\n'.encode(),data,b'\r\n']
 body += [f'--{boundary}--\r\n'.encode()];req=Request(BASE+path,data=b''.join(body),headers={'Content-Type':f'multipart/form-data; boundary={boundary}'})
 try:
  with urlopen(req,timeout=60) as r:return r.status,json.loads(r.read())
 except Exception as e:return 0,{'error':str(e)}
def check(name,ok,detail): results[name]={'pass':bool(ok),'detail':detail};assert ok,name
def main():
 _,live=get('/health/live'); _,ready=get('/health/ready');check('health',live['status']=='live' and ready['database'],ready)
 _,models=get('/api/v1/models'); ready_ids={x['id'] for x in models if x['ready']};check('models',{'chilli_disease_v1','tomato_disease_plantvillage_v1'}<=ready_ids,models)
 status,tomato=post('/api/v1/inspections',{'crop_hint':'tomato','plant_part_hint':'leaf'},'tomato_leaf.jpg',(ASSETS/'tomato_leaf.jpg').read_bytes());check('tomato',status==200 and tomato['status']=='completed' and tomato['selected_model']['model_id']=='tomato_disease_plantvillage_v1' and tomato['prediction'],tomato)
 status,chilli=post('/api/v1/inspections',{'crop_hint':'chilli','plant_part_hint':'leaf'},'chilli_leaf.jpg',(ASSETS/'chilli_leaf.jpg').read_bytes());check('chilli',status==200 and chilli['status']=='completed' and chilli['selected_model']['model_id']=='chilli_disease_v1' and chilli['prediction'],chilli)
 status,no_crop=post('/api/v1/inspections',{},'chilli_leaf.jpg',(ASSETS/'chilli_leaf.jpg').read_bytes());check('no_crop',status==200 and no_crop['status']=='needs_crop_confirmation' and no_crop['prediction'] is None,no_crop)
 status,fruit=post('/api/v1/inspections',{'crop_hint':'tomato','plant_part_hint':'fruit'},'fruit.jpg',(ASSETS/'fruit.jpg').read_bytes());check('fruit',status==200 and fruit['status']=='unsupported_plant_part' and fruit['prediction'] is None,fruit)
 status,bad=post('/api/v1/inspections',{'crop_hint':'tomato'},'invalid.txt',b'not an image');check('invalid_image',status==200 and bad['status']=='invalid_image' and bad['prediction'] is None,bad)
 _,stored=get('/api/v1/inspections/'+tomato['inspection_id']); _,listed=get('/api/v1/inspections');check('persistence',stored['prediction']['prediction_id']==tomato['prediction']['prediction_id'] and stored['identification']['crop']=='tomato' and any(x['inspection_id']==tomato['inspection_id'] for x in listed),stored)
 status,direct=post('/api/v1/predictions',{'model_id':'chilli_disease_v1'},'chilli_leaf.jpg',(ASSETS/'chilli_leaf.jpg').read_bytes());check('direct_prediction',status==200 and direct.get('prediction_id'),direct)
 Path(__file__).parents[1]/'reports'/'quick_test_results.json'; out=Path(__file__).parents[1]/'reports'/'quick_test_results.json';out.write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
if __name__=='__main__':
 try:main()
 except Exception as e:
  print(json.dumps(results,indent=2));sys.exit(1)
