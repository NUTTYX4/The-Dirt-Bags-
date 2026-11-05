import io,uuid,logging
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI,UploadFile,File,Form,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import text,select
from .config import settings
from .db import Session,ChatSession,ChatMessage,Prediction,Inspection
from .models import registry
from .ai_provider import ai
app=FastAPI(title='CropScope AI API',version='1.0.0');app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origins.split(','),allow_methods=['*'],allow_headers=['*'])
logger=logging.getLogger(__name__)
def valid_image(f:UploadFile,b:bytes):
 if len(b)>settings.max_upload_bytes or f.content_type not in {'image/jpeg','image/png','image/webp'}:raise HTTPException(415,'Unsupported or oversized image')
 try:
  from PIL import Image
  Image.open(io.BytesIO(b)).verify()
 except Exception:raise HTTPException(422,'Invalid image')
def inspection_response(q,prediction=None,message=None,assistant_message=None):
 if message is None:
  message={'completed':'Local CropScope leaf-model result.','low_confidence':'The local model result is uncertain; upload a clearer leaf photo.','needs_crop_confirmation':'Crop could not be identified. Upload a clearer tomato or chilli leaf photo.','unsupported_crop':'Only tomato and chilli leaf models are currently available.','unsupported_plant_part':'Current verified models support leaf images only.','invalid_image':'Unsupported or invalid image.','failed':'The inspection could not be completed.'}.get(q.status)
 if assistant_message is None: assistant_message=(q.metadata_json or {}).get('assistant_message')
 metadata=q.metadata_json or {}
 routing_metadata={key:metadata[key] for key in ('gemini_image_routing_consent','ai_request_success','ai_failure_reason','image_quality','needs_confirmation','routing_observations','fallback_reason') if key in metadata}
 return {'inspection_id':q.id,'status':q.status,'identification':{'crop':q.crop,'plant_part':q.plant_part,'source':q.identification_source,'certainty':q.identification_certainty},'selected_model':{'model_id':q.selected_model_id,'status':'ready'} if q.selected_model_id else None,'prediction':prediction,'assistant_message':assistant_message,'inference_time_ms':prediction.get('inference_time_ms') if prediction else None,'message':message,'next_action':'upload_a_clear_leaf_photo' if q.status=='unsupported_plant_part' else ('select_crop' if q.status in {'needs_crop_confirmation','identification_failed'} else None),'routing_metadata':routing_metadata,'created_at':q.created_at}

def record_chat(s,session_id,role,content,blocks=None):
 if session_id:
  s.add(ChatMessage(session_id=session_id,role=role,content=content,ui_blocks=blocks or []))
  session=s.get(ChatSession,session_id)
  if session:session.updated_at=datetime.utcnow()

@app.get('/health/live')
def live():return {'status':'live'}
@app.get('/health/ready')
def ready():
 try:
  with Session() as s:s.execute(text('select 1'))
  db=True
 except Exception:db=False
 return {'ready':db,'database':db,'models':registry.details(),'ai':ai.status()}
@app.get('/api/v1/models')
def models():return registry.details()
@app.get('/api/v1/models/{model_id}')
def model(model_id:str):
 for x in registry.details():
  if x['id']==model_id:return x
 raise HTTPException(404,'Model not found')
@app.post('/api/v1/predictions')
async def predict(model_id:str=Form(...),image:UploadFile=File(...),top_k:int=Form(3)):
 b=await image.read();valid_image(image,b)
 try:r=registry.predict(model_id,io.BytesIO(b),top_k)
 except ValueError as e:raise HTTPException(400,str(e))
 with Session() as s:
  q=Prediction(model_id=model_id,predicted_label=r['predicted_label'],confidence=r['confidence'],top_k=r['top_k'],inference_time_ms=r['inference_time_ms']);s.add(q);s.commit();r['prediction_id']=q.id
 return r
@app.get('/api/v1/predictions/{prediction_id}')
def prediction(prediction_id:str):
 with Session() as s:
  p=s.get(Prediction,prediction_id)
  if not p:raise HTTPException(404,'Prediction not found')
  return {'prediction_id':p.id,'model_id':p.model_id,'predicted_label':p.predicted_label,'confidence':p.confidence,'top_k':p.top_k,'inference_time_ms':p.inference_time_ms}
@app.post('/api/v1/inspections')
async def inspect(image:UploadFile=File(...),session_id:str|None=Form(None),crop_hint:str|None=Form(None),plant_part_hint:str|None=Form(None),gemini_image_routing_consent:bool=Form(False)):
 b=await image.read()
 try: valid_image(image,b)
 except HTTPException as e:
  with Session() as s:q=Inspection(status='invalid_image',error_code='invalid_image');s.add(q);s.commit();return inspection_response(q,message=e.detail)
 crop=(crop_hint or '').lower().strip(); part=(plant_part_hint or '').lower().strip(); route=None; routing_failure=None; ai_success=None
 if not crop and gemini_image_routing_consent:
  route,routing_failure=ai.identify(b,image.content_type or 'image/jpeg');ai_success=route is not None
  if route and not route.requires_confirmation(): crop=route.crop;part=route.plant_part
 with Session() as s:
  if session_id and not s.get(ChatSession,session_id):raise HTTPException(404,'Session not found')
  key=f'{uuid.uuid4()}{Path(image.filename or "upload.jpg").suffix.lower() or ".jpg"}'; Path('/data/uploads').mkdir(parents=True,exist_ok=True);Path('/data/uploads',key).write_bytes(b)
  identified_crop=route.crop if route else crop;identified_part=route.plant_part if route else part
  q=Inspection(session_id=session_id,attachment_key=key,crop=identified_crop or None,plant_part=identified_part or None,identification_source='automatic_ai' if route else ('manual_hint' if crop else 'none'),identification_certainty=route.certainty if route else ('high' if crop else 'unknown'),status='identifying',metadata_json={'gemini_image_routing_consent':gemini_image_routing_consent,'ai_request_success':ai_success,'ai_failure_reason':routing_failure,'image_quality':route.image_quality if route else None,'needs_confirmation':route.requires_confirmation() if route else False,'routing_observations':route.observations if route else []});s.add(q);s.flush();record_chat(s,session_id,'user','Uploaded plant photograph.',[{'type':'inspection_image','inspection_id':q.id}])
  # Images never leave this service unless explicit consent and a configured visual router exists.
  if not crop:
   if gemini_image_routing_consent and not route:
    q.status='identification_failed';q.error_code=routing_failure or 'ai_request_failed';q.metadata_json={**q.metadata_json,'fallback_reason':'automatic_identification_unavailable'};message='Automatic crop identification is temporarily unavailable. Select Tomato or Chilli manually to continue.';record_chat(s,session_id,'assistant',message);s.commit();logger.warning('Inspection %s automatic routing failed: %s',q.id,q.error_code);return inspection_response(q,message=message)
   q.status='needs_crop_confirmation';q.user_confirmation_required=True;q.metadata_json={**q.metadata_json,'fallback_reason':'uncertain_crop_or_image'};message='Crop or plant part is unclear. Upload a clearer tomato or chilli leaf photo, or select the crop manually.';record_chat(s,session_id,'assistant',message);s.commit();return inspection_response(q,message=message)
  if crop not in {'tomato','chilli'}:
   q.status='unsupported_crop';q.error_code='unsupported_crop';s.commit();return inspection_response(q,message='Only tomato and chilli leaf models are currently available.')
  if part!='leaf':
   q.status='unsupported_plant_part';q.error_code='unsupported_plant_part';s.commit();return inspection_response(q,message='Current verified models support leaf images only.')
  model=registry.route(crop,part)
  if not model:q.status='failed';q.error_code='model_unavailable';s.commit();return inspection_response(q,message='No verified ready model is available.')
  try:r=registry.predict(model['id'],io.BytesIO(b),3)
  except Exception:q.status='failed';q.error_code='inference_failed';s.commit();return inspection_response(q,message='Local inference failed; no prediction was created.')
  p=Prediction(session_id=session_id,model_id=model['id'],predicted_label=r['predicted_label'],confidence=r['confidence'],top_k=r['top_k'],inference_time_ms=r['inference_time_ms']);s.add(p);s.flush();r['prediction_id']=p.id;r['predicted_class']=r['predicted_label'];r['top_predictions']=r['top_k'];q.selected_model_id=model['id'];q.prediction_id=p.id;q.status='completed' if r['confidence']>=float(model.get('confidence_threshold',0)) else 'low_confidence';q.completed_at=datetime.utcnow();session=s.get(ChatSession,session_id) if session_id else None
  if session:session.title=f'{crop.title()} leaf inspection'
  summary=f"CropScope local result: {r['predicted_label']} ({r['confidence']:.1%} confidence)."
  advice=ai.reply('Explain the verified local result for the farmer.',r)
  q.metadata_json={**(q.metadata_json or {}),'assistant_message':advice}
  record_chat(s,session_id,'assistant',summary,[{'type':'prediction_card','data':r,'inspection_id':q.id}])
  record_chat(s,session_id,'assistant',advice)
  s.commit();return inspection_response(q,r,'Local CropScope leaf-model result.',advice)
@app.get('/api/v1/inspections/{inspection_id}')
def get_inspection(inspection_id:str):
 with Session() as s:
  q=s.get(Inspection,inspection_id)
  if not q:raise HTTPException(404,'Inspection not found')
  p=s.get(Prediction,q.prediction_id) if q.prediction_id else None; pred={'prediction_id':p.id,'predicted_class':p.predicted_label,'confidence':p.confidence,'top_predictions':p.top_k,'inference_time_ms':p.inference_time_ms} if p else None;return inspection_response(q,pred)
@app.get('/api/v1/inspections')
def list_inspections(session_id:str|None=None,limit:int=20,offset:int=0):
 with Session() as s:
  query=select(Inspection).where(Inspection.session_id==session_id) if session_id else select(Inspection)
  rows=s.scalars(query.order_by(Inspection.created_at.desc()).offset(offset).limit(min(limit,100))).all();return [inspection_response(x) for x in rows]
@app.get('/api/v1/inspections/{inspection_id}/image')
def inspection_image(inspection_id:str):
 with Session() as s:
  q=s.get(Inspection,inspection_id)
  if not q or not q.attachment_key:raise HTTPException(404,'Inspection image not found')
  path=Path('/data/uploads',q.attachment_key)
  if not path.is_file():raise HTTPException(404,'Inspection image not found')
  return FileResponse(path)
@app.post('/api/v1/chat/sessions')
def create_session(title:str='New CropScope chat'):
 with Session() as s:q=ChatSession(title=title);s.add(q);s.commit();return {'session_id':q.id,'title':q.title}
@app.get('/api/v1/chat/sessions')
def list_sessions(limit:int=50):
 with Session() as s:return [{'session_id':x.id,'title':x.title,'created_at':x.created_at,'updated_at':x.updated_at} for x in s.scalars(select(ChatSession).order_by(ChatSession.updated_at.desc()).limit(min(limit,100)))]
@app.get('/api/v1/chat/sessions/{session_id}')
def get_session(session_id:str):
 with Session() as s:
  q=s.get(ChatSession,session_id)
  if not q:raise HTTPException(404,'Session not found')
  return {'session_id':q.id,'title':q.title,'created_at':q.created_at,'updated_at':q.updated_at}
@app.get('/api/v1/chat/sessions/{session_id}/messages')
def messages(session_id:str):
 with Session() as s:return [{'id':x.id,'role':x.role,'content':x.content,'ui_blocks':x.ui_blocks,'created_at':x.created_at} for x in s.scalars(select(ChatMessage).where(ChatMessage.session_id==session_id).order_by(ChatMessage.created_at))]
@app.post('/api/v1/chat/sessions/{session_id}/messages')
async def message(session_id:str,text:str=Form(''),model_id:str|None=Form(None),image:UploadFile|None=File(None)):
 with Session() as s:
  session=s.get(ChatSession,session_id)
  if not session:raise HTTPException(404,'Session not found')
  s.add(ChatMessage(session_id=session_id,role='user',content=text));pred=None
  if image:
   b=await image.read();valid_image(image,b)
   if not model_id:raise HTTPException(400,'Select a model for image analysis')
   pred=registry.predict(model_id,io.BytesIO(b),3);q=Prediction(session_id=session_id,model_id=model_id,predicted_label=pred['predicted_label'],confidence=pred['confidence'],top_k=pred['top_k'],inference_time_ms=pred['inference_time_ms']);s.add(q);s.flush();pred['prediction_id']=q.id
  if not pred:
   latest=s.scalars(select(Prediction).where(Prediction.session_id==session_id).order_by(Prediction.created_at.desc()).limit(1)).first()
   if latest:pred={'prediction_id':latest.id,'model_id':latest.model_id,'predicted_label':latest.predicted_label,'confidence':latest.confidence,'top_k':latest.top_k,'inference_time_ms':latest.inference_time_ms}
  content=ai.reply(text,pred);blocks=[{'type':'prediction_card','data':pred}] if pred else [{'type':'text','data':content}];a=ChatMessage(session_id=session_id,role='assistant',content=content,ui_blocks=blocks);s.add(a);session.updated_at=datetime.utcnow();s.commit();return {'session_id':session_id,'message_id':a.id,'assistant_message':{'role':'assistant','content':content},'ui_blocks':blocks,'prediction':pred,'tool_calls':[],'created_at':a.created_at}
