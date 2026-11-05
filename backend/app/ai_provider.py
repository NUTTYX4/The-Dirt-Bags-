"""Provider-neutral external AI routing. Local ONNX models remain disease authority."""
import base64,hashlib,json
from datetime import datetime,timedelta
from typing import Literal
from openai import OpenAI,APIStatusError
from pydantic import BaseModel,Field,ValidationError
from sqlalchemy import select
from .config import settings
from .db import Session,AIUsage,AIIdentificationCache,AICooldown

class CropRouting(BaseModel):
 crop:Literal['tomato','chilli','other','unknown'];plant_part:Literal['leaf','fruit','stem','flower','whole_plant','unknown'];certainty:Literal['high','medium','low'];image_quality:Literal['acceptable','poor'];needs_confirmation:bool;observations:list[str]=Field(default_factory=list,max_length=4)
 def requires_confirmation(self):return self.crop=='unknown' or self.certainty=='low' or self.image_quality=='poor'
class AIProvider:
 def __init__(self):self.client=OpenAI(base_url=settings.openrouter_base_url,api_key=settings.openrouter_api_key,timeout=settings.ai_timeout_seconds,max_retries=0) if settings.ai_enabled and settings.openrouter_api_key and settings.openrouter_model else None
 def status(self):return {'enabled':settings.ai_enabled,'configured':bool(self.client),'provider':settings.ai_provider}
 def reserve(self):
  now=datetime.utcnow();buckets=[(f'minute:{now:%Y%m%d%H%M}',settings.ai_max_requests_per_minute),(f'day:{now:%Y%m%d}',settings.ai_max_requests_per_day)]
  with Session.begin() as s:
   cooldown=s.get(AICooldown,settings.ai_provider)
   if cooldown and cooldown.expires_at>now:return False,'ai_rate_limited'
   for bucket,limit in buckets:
    row=s.get(AIUsage,bucket)
    if row and row.count>=limit:return False,'ai_rate_limited'
   for bucket,_ in buckets:
    row=s.get(AIUsage,bucket)
    if row:row.count+=1
    else:s.add(AIUsage(bucket=bucket,count=1))
  return True,None
 def note_provider_429(self,headers):
  try:seconds=max(1,min(int(headers.get('retry-after','60')),3600))
  except (TypeError,ValueError):seconds=60
  with Session.begin() as s:s.merge(AICooldown(provider=settings.ai_provider,expires_at=datetime.utcnow()+timedelta(seconds=seconds)))
 def completion(self,messages,max_tokens=None,json_mode=False):
  if not self.client:return None,'ai_not_configured'
  allowed,reason=self.reserve()
  if not allowed:return None,reason
  try:
   options={'model':settings.openrouter_model,'messages':messages,'max_tokens':max_tokens or settings.ai_max_output_tokens,'temperature':0}
   if json_mode:
    options['response_format']={'type':'json_object'}
    options['extra_body']={'reasoning':{'effort':'low','exclude':True}}
   return self.client.chat.completions.create(**options),None
  except APIStatusError as exc:
   if exc.status_code==429:self.note_provider_429(exc.response.headers);return None,'ai_quota_exhausted'
   return None,'ai_request_failed'
  except Exception:return None,'ai_request_failed'
 def identify(self,data:bytes,mime_type:str):
  digest=hashlib.sha256(data).hexdigest()
  with Session() as s:
   cached=s.get(AIIdentificationCache,digest)
   if cached:
    try:return CropRouting.model_validate(cached.response_json),None
    except ValidationError:pass
  prompt='Inspect the supplied farmer photograph. Identify the visible crop and plant part only, never a disease. This service supports tomato and chilli; if a clear tomato or chilli leaf is visible, choose tomato or chilli and leaf rather than unknown. Use unknown only when the photograph genuinely cannot establish a crop or plant part. Return one JSON object only with exactly: crop (tomato/chilli/other/unknown), plant_part (leaf/fruit/stem/flower/whole_plant/unknown), certainty (high/medium/low), image_quality (acceptable/poor), needs_confirmation (boolean), observations (a short array).'
  url=f'data:{mime_type};base64,{base64.b64encode(data).decode()}'
  response,error=self.completion([{'role':'user','content':[{'type':'text','text':prompt},{'type':'image_url','image_url':{'url':url}}]}],settings.ai_routing_max_output_tokens,True)
  if error:return None,error
  try:
   content=response.choices[0].message.content or '{}';content=content.removeprefix('```json').removeprefix('```').removesuffix('```').strip();route=CropRouting.model_validate(json.loads(content))
   if route.crop=='unknown' or route.certainty=='low' or route.image_quality=='poor':route.needs_confirmation=True
   with Session.begin() as s:s.merge(AIIdentificationCache(image_sha256=digest,response_json=route.model_dump()))
   return route,None
  except (json.JSONDecodeError,ValidationError):return None,'ai_malformed_response'
 def reply(self,text,prediction=None):
  context=f'Verified local prediction: {prediction.get("predicted_label")} at {prediction.get("confidence",0):.1%}.' if prediction else 'No local prediction is available.'
  response,error=self.completion([{'role':'system','content':'You are CropScope AI. Give concise, cautious agricultural guidance. Never invent model results, numeric confidence, or pesticide doses.'},{'role':'user','content':f'{context}\nFarmer question: {text}'}])
  if error:return 'Local prediction is saved. AI explanation is temporarily unavailable.'
  return (response.choices[0].message.content or 'Local prediction is saved.').strip()
ai=AIProvider()
