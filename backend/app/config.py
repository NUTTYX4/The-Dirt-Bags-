from pydantic_settings import BaseSettings,SettingsConfigDict
class Settings(BaseSettings):
 model_config=SettingsConfigDict(env_file='.env',extra='ignore')
 database_url:str='postgresql+psycopg://cropscope:change-me@db:5432/cropscope'
 gemini_enabled:bool=False; gemini_api_key:str=''; gemini_model:str='gemini-flash-latest'; gemini_max_output_tokens:int=512; gemini_temperature:float=.2; gemini_timeout_seconds:int=20
 cors_origins:str='http://localhost:3000,http://127.0.0.1:3000'; max_upload_bytes:int=10485760
settings=Settings()
