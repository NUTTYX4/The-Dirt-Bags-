import uuid
from datetime import datetime
from sqlalchemy import create_engine,String,Text,DateTime,ForeignKey,Float,JSON
from sqlalchemy.orm import DeclarativeBase,mapped_column,Mapped,sessionmaker
from .config import settings
engine=create_engine(settings.database_url,pool_pre_ping=True); Session=sessionmaker(bind=engine,expire_on_commit=False)
class Base(DeclarativeBase): pass
class ChatSession(Base):
 __tablename__='chat_sessions'; id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid.uuid4())); title:Mapped[str]=mapped_column(String(200),default='New CropScope chat'); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
class ChatMessage(Base):
 __tablename__='chat_messages'; id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid.uuid4())); session_id:Mapped[str]=mapped_column(ForeignKey('chat_sessions.id',ondelete='CASCADE')); role:Mapped[str]=mapped_column(String(20)); content:Mapped[str]=mapped_column(Text); ui_blocks:Mapped[list]=mapped_column(JSON,default=list); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Prediction(Base):
 __tablename__='prediction_records'; id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid.uuid4())); session_id:Mapped[str|None]=mapped_column(String(36),nullable=True); model_id:Mapped[str]=mapped_column(String(100)); predicted_label:Mapped[str]=mapped_column(String(255)); confidence:Mapped[float]=mapped_column(Float); top_k:Mapped[list]=mapped_column(JSON); inference_time_ms:Mapped[float]=mapped_column(Float); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Inspection(Base):
 __tablename__='inspections'; id:Mapped[str]=mapped_column(String(36),primary_key=True,default=lambda:str(uuid.uuid4())); session_id:Mapped[str|None]=mapped_column(String(36),nullable=True); attachment_key:Mapped[str|None]=mapped_column(String(255),nullable=True); crop:Mapped[str|None]=mapped_column(String(40),nullable=True); plant_part:Mapped[str|None]=mapped_column(String(40),nullable=True); identification_source:Mapped[str]=mapped_column(String(40),default='manual'); identification_certainty:Mapped[str]=mapped_column(String(20),default='unknown'); selected_model_id:Mapped[str|None]=mapped_column(String(100),nullable=True); prediction_id:Mapped[str|None]=mapped_column(String(36),nullable=True); status:Mapped[str]=mapped_column(String(40)); error_code:Mapped[str|None]=mapped_column(String(80),nullable=True); user_confirmation_required:Mapped[bool]=mapped_column(default=False); metadata_json:Mapped[dict]=mapped_column(JSON,default=dict); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); completed_at:Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
class AIUsage(Base):
 __tablename__='ai_usage'; bucket:Mapped[str]=mapped_column(String(40),primary_key=True); count:Mapped[int]=mapped_column(default=0); updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
class AIIdentificationCache(Base):
 __tablename__='ai_identification_cache'; image_sha256:Mapped[str]=mapped_column(String(64),primary_key=True); response_json:Mapped[dict]=mapped_column(JSON); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class AICooldown(Base):
 __tablename__='ai_cooldowns'; provider:Mapped[str]=mapped_column(String(40),primary_key=True); expires_at:Mapped[datetime]=mapped_column(DateTime); updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
