import io
from fastapi import FastAPI,UploadFile,File,Form,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text,select
from .config import settings
from .db import Session,ChatSession,ChatMessage,Prediction
from .models import registry
from .gemini import gemini
app=FastAPI(title='CropScope AI API',version='1.0.0');app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origins.split(','),allow_methods=['*'],allow_headers=['*'])
def valid_image(f:UploadFile,b:bytes):
 if len(b)>settings.max_upload_bytes or f.content_type not in {'image/jpeg','image/png','image/webp'}:raise HTTPException(415,'Unsupported or oversized image')
 try:
  from PIL import Image
  Image.open(io.BytesIO(b)).verify()
 except Exception:raise HTTPException(422,'Invalid image')
@app.get('/health/live')
def live():return {'status':'live'}
@app.get('/health/ready')
def ready():
 try:
  with Session() as s:s.execute(text('select 1'))
  db=True
 except Exception:db=False
 return {'ready':db,'database':db,'models':registry.details(),'gemini':gemini.status()}
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
@app.post('/api/v1/chat/sessions')
def create_session(title:str='New CropScope chat'):
 with Session() as s:q=ChatSession(title=title);s.add(q);s.commit();return {'session_id':q.id,'title':q.title}
@app.get('/api/v1/chat/sessions/{session_id}/messages')
def messages(session_id:str):
 with Session() as s:return [{'id':x.id,'role':x.role,'content':x.content,'ui_blocks':x.ui_blocks,'created_at':x.created_at} for x in s.scalars(select(ChatMessage).where(ChatMessage.session_id==session_id).order_by(ChatMessage.created_at))]
@app.post('/api/v1/chat/sessions/{session_id}/messages')
async def message(session_id:str,text:str=Form(''),model_id:str|None=Form(None),image:UploadFile|None=File(None)):
 with Session() as s:
  if not s.get(ChatSession,session_id):raise HTTPException(404,'Session not found')
  s.add(ChatMessage(session_id=session_id,role='user',content=text));pred=None
  if image:
   b=await image.read();valid_image(image,b)
   if not model_id:raise HTTPException(400,'Select a model for image analysis')
   pred=registry.predict(model_id,io.BytesIO(b),3);q=Prediction(session_id=session_id,model_id=model_id,predicted_label=pred['predicted_label'],confidence=pred['confidence'],top_k=pred['top_k'],inference_time_ms=pred['inference_time_ms']);s.add(q);s.flush();pred['prediction_id']=q.id
  content=gemini.reply(text,pred);blocks=[{'type':'prediction_card','data':pred}] if pred else [{'type':'text','data':content}];a=ChatMessage(session_id=session_id,role='assistant',content=content,ui_blocks=blocks);s.add(a);s.commit();return {'session_id':session_id,'message_id':a.id,'assistant_message':{'role':'assistant','content':content},'ui_blocks':blocks,'prediction':pred,'tool_calls':[],'created_at':a.created_at}
