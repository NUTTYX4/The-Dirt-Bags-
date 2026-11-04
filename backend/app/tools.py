"""Strict tool allowlist for Gemini orchestration; no shell, SQL, or filesystem tools."""
ALLOWED_TOOLS={'list_supported_models','get_model_details','analyze_uploaded_crop_image','get_prediction_result','get_recent_predictions','get_chat_context'}
def validate_tool(name:str):
 if name not in ALLOWED_TOOLS: raise ValueError('Tool is not allowed')
