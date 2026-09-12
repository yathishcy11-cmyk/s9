from datetime import datetime
from sqlalchemy import String,Integer,BigInteger,DateTime,ForeignKey,Text,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column
from .db import Base
class User(Base):
    __tablename__='users'; id:Mapped[int]=mapped_column(primary_key=True); email:Mapped[str]=mapped_column(String(255),unique=True,index=True); password_hash:Mapped[str]=mapped_column(String(255)); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class FileObject(Base):
    __tablename__='files'; id:Mapped[int]=mapped_column(primary_key=True); owner_id:Mapped[int]=mapped_column(ForeignKey('users.id'),index=True); filename:Mapped[str]=mapped_column(String(500)); content_type:Mapped[str]=mapped_column(String(255),default='application/octet-stream'); latest_version:Mapped[int]=mapped_column(Integer,default=1); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow); updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class FileVersion(Base):
    __tablename__='file_versions'; __table_args__=(UniqueConstraint('file_id','version'),); id:Mapped[int]=mapped_column(primary_key=True); file_id:Mapped[int]=mapped_column(ForeignKey('files.id'),index=True); version:Mapped[int]=mapped_column(Integer); size_bytes:Mapped[int]=mapped_column(BigInteger); chunk_size:Mapped[int]=mapped_column(Integer); total_chunks:Mapped[int]=mapped_column(Integer); checksum:Mapped[str|None]=mapped_column(String(64),nullable=True); status:Mapped[str]=mapped_column(String(32),default='uploading'); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class Chunk(Base):
    __tablename__='chunks'; __table_args__=(UniqueConstraint('version_id','chunk_index'),); id:Mapped[int]=mapped_column(primary_key=True); version_id:Mapped[int]=mapped_column(ForeignKey('file_versions.id'),index=True); chunk_index:Mapped[int]=mapped_column(Integer); size_bytes:Mapped[int]=mapped_column(Integer); checksum:Mapped[str]=mapped_column(String(64)); replica_nodes:Mapped[str]=mapped_column(Text); created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
