from .config import settings
from google import genai
class Gemini:
 def __init__(self): self.client=genai.Client(api_key=settings.gemini_api_key) if settings.gemini_enabled and settings.gemini_api_key else None
 def status(self): return {'enabled':settings.gemini_enabled,'configured':bool(self.client)}
 def reply(self,text,prediction=None):
  if prediction:return f"Local CropScope model result: {prediction['predicted_label']} ({prediction['confidence']:.1%}). This is a preliminary image-based result; field confirmation is recommended."
  if self.client:
   try:return self.client.models.generate_content(model=settings.gemini_model,contents=f"You are CropScope AI. Give brief, cautious crop guidance. Never invent local model predictions. User: {text}").text
   except Exception:return 'Conversational assistance is temporarily unavailable. Local image prediction remains available.'
  return 'Conversational assistance is unavailable until GEMINI_API_KEY is configured. Local image prediction remains available.'
gemini=Gemini()
