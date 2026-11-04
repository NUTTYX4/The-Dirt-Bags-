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
