from pydantic_settings import BaseSettings,SettingsConfigDict
class Settings(BaseSettings):
 model_config=SettingsConfigDict(env_file='.env',extra='ignore')
 database_url:str='postgresql+psycopg://cropscope:change-me@db:5432/cropscope'
 ai_provider:str='openrouter';ai_enabled:bool=False;openrouter_api_key:str='';openrouter_base_url:str='https://openrouter.ai/api/v1';openrouter_model:str='';ai_max_requests_per_minute:int=5;ai_max_requests_per_day:int=40;ai_max_output_tokens:int=512;ai_routing_max_output_tokens:int=1536;ai_timeout_seconds:int=25
 cors_origins:str='http://localhost:3000,http://127.0.0.1:3000';max_upload_bytes:int=10485760
settings=Settings()
