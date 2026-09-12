import os,json,math,hashlib
from datetime import datetime
from fastapi import FastAPI,Depends,HTTPException,UploadFile,File,Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select,desc
import redis.asyncio as redis
from .db import Base,engine,get_db
from .models import User,FileObject,FileVersion,Chunk
from .schemas import RegisterIn,LoginIn,UploadStartIn,UploadCompleteIn
from .auth import hash_password,verify_password,create_token,current_user
from .storage import put_chunk,get_chunk,healthy_nodes
Base.metadata.create_all(bind=engine)
app=FastAPI(title='Distributed Cloud Storage API',version='1.0.0')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_credentials=False,allow_methods=['*'],allow_headers=['*'])
CHUNK_SIZE=int(os.getenv('CHUNK_SIZE',str(5*1024*1024))); RF=int(os.getenv('REPLICATION_FACTOR','2')); cache=redis.from_url(os.getenv('REDIS_URL','redis://redis:6379/0'),decode_responses=True)
@app.get('/health')
async def health():
    n=await healthy_nodes(); return {'status':'ok','healthy_storage_nodes':n,'count':len(n),'replication_factor':RF,'chunk_size':CHUNK_SIZE}
@app.post('/auth/register')
def register(data:RegisterIn,db:Session=Depends(get_db)):
    if db.scalar(select(User).where(User.email==data.email.lower())): raise HTTPException(409,'Email already registered')
    u=User(email=data.email.lower(),password_hash=hash_password(data.password)); db.add(u);db.commit();db.refresh(u); return {'token':create_token(u.id),'user':{'id':u.id,'email':u.email}}
@app.post('/auth/login')
def login(data:LoginIn,db:Session=Depends(get_db)):
    u=db.scalar(select(User).where(User.email==data.email.lower()))
    if not u or not verify_password(data.password,u.password_hash): raise HTTPException(401,'Invalid credentials')
    return {'token':create_token(u.id),'user':{'id':u.id,'email':u.email}}
@app.post('/uploads/start')
def start_upload(data:UploadStartIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    if data.existing_file_id:
        obj=db.get(FileObject,data.existing_file_id)
        if not obj or obj.owner_id!=user.id: raise HTTPException(404,'File not found')
        version_no=obj.latest_version+1; obj.latest_version=version_no; obj.updated_at=datetime.utcnow(); obj.filename=data.filename; obj.content_type=data.content_type
    else:
        obj=FileObject(owner_id=user.id,filename=data.filename,content_type=data.content_type,latest_version=1);db.add(obj);db.flush();version_no=1
    total=math.ceil(data.size_bytes/CHUNK_SIZE); v=FileVersion(file_id=obj.id,version=version_no,size_bytes=data.size_bytes,chunk_size=CHUNK_SIZE,total_chunks=total,status='uploading');db.add(v);db.commit();db.refresh(v)
    return {'file_id':obj.id,'version_id':v.id,'version':version_no,'chunk_size':CHUNK_SIZE,'total_chunks':total}
@app.get('/uploads/{version_id}/status')
def upload_status(version_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    v=db.get(FileVersion,version_id)
    if not v: raise HTTPException(404,'Upload not found')
    obj=db.get(FileObject,v.file_id)
    if obj.owner_id!=user.id: raise HTTPException(403,'Forbidden')
    uploaded=list(db.scalars(select(Chunk.chunk_index).where(Chunk.version_id==version_id).order_by(Chunk.chunk_index)).all()); return {'uploaded_chunks':uploaded,'total_chunks':v.total_chunks,'status':v.status}
@app.put('/uploads/{version_id}/chunks/{chunk_index}')
async def upload_chunk(version_id:int,chunk_index:int,part:UploadFile=File(...),user:User=Depends(current_user),db:Session=Depends(get_db)):
    v=db.get(FileVersion,version_id)
    if not v: raise HTTPException(404,'Upload not found')
    obj=db.get(FileObject,v.file_id)
    if obj.owner_id!=user.id: raise HTTPException(403,'Forbidden')
    if not 0<=chunk_index<v.total_chunks: raise HTTPException(400,'Invalid chunk index')
    if db.scalar(select(Chunk).where(Chunk.version_id==version_id,Chunk.chunk_index==chunk_index)): return {'status':'already_uploaded','chunk_index':chunk_index}
    data=await part.read(); expected=v.chunk_size if chunk_index<v.total_chunks-1 else v.size_bytes-(v.total_chunks-1)*v.chunk_size
    if len(data)>expected: raise HTTPException(413,'Chunk too large')
    checksum,nodes=await put_chunk(version_id,chunk_index,data); db.add(Chunk(version_id=version_id,chunk_index=chunk_index,size_bytes=len(data),checksum=checksum,replica_nodes=json.dumps(nodes)));db.commit(); return {'status':'stored','chunk_index':chunk_index,'checksum':checksum,'replicas':nodes}
@app.post('/uploads/{version_id}/complete')
async def complete_upload(version_id:int,data:UploadCompleteIn,user:User=Depends(current_user),db:Session=Depends(get_db)):
    v=db.get(FileVersion,version_id)
    if not v: raise HTTPException(404,'Upload not found')
    obj=db.get(FileObject,v.file_id)
    if obj.owner_id!=user.id: raise HTTPException(403,'Forbidden')
    count=len(db.scalars(select(Chunk).where(Chunk.version_id==version_id)).all())
    if count!=v.total_chunks: raise HTTPException(409,f'Upload incomplete: {count}/{v.total_chunks}')
    v.status='ready';v.checksum=data.file_checksum;db.commit()
    try: await cache.delete(f'files:{user.id}')
    except: pass
    return {'status':'ready','file_id':obj.id,'version':v.version}
@app.get('/files')
async def list_files(user:User=Depends(current_user),db:Session=Depends(get_db)):
    key=f'files:{user.id}'
    try:
        hit=await cache.get(key)
        if hit:return {'cached':True,'files':json.loads(hit)}
    except:pass
    rows=db.scalars(select(FileObject).where(FileObject.owner_id==user.id).order_by(desc(FileObject.updated_at))).all();out=[]
    for f in rows:
        v=db.scalar(select(FileVersion).where(FileVersion.file_id==f.id,FileVersion.version==f.latest_version));out.append({'id':f.id,'filename':f.filename,'content_type':f.content_type,'version':f.latest_version,'size_bytes':v.size_bytes if v else 0,'status':v.status if v else 'unknown','updated_at':f.updated_at.isoformat()})
    try: await cache.setex(key,30,json.dumps(out))
    except:pass
    return {'cached':False,'files':out}
@app.get('/files/{file_id}/versions')
def versions(file_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    obj=db.get(FileObject,file_id)
    if not obj or obj.owner_id!=user.id: raise HTTPException(404,'File not found')
    vs=db.scalars(select(FileVersion).where(FileVersion.file_id==file_id).order_by(desc(FileVersion.version))).all();return [{'version':v.version,'size_bytes':v.size_bytes,'status':v.status,'created_at':v.created_at.isoformat()} for v in vs]
@app.get('/files/{file_id}/download')
async def download(file_id:int,version:int|None=Query(default=None),user:User=Depends(current_user),db:Session=Depends(get_db)):
    obj=db.get(FileObject,file_id)
    if not obj or obj.owner_id!=user.id: raise HTTPException(404,'File not found')
    wanted=version or obj.latest_version;v=db.scalar(select(FileVersion).where(FileVersion.file_id==file_id,FileVersion.version==wanted))
    if not v or v.status!='ready': raise HTTPException(404,'Ready version not found')
    chunks=db.scalars(select(Chunk).where(Chunk.version_id==v.id).order_by(Chunk.chunk_index)).all()
    async def stream():
        for c in chunks:yield await get_chunk(v.id,c.chunk_index,json.loads(c.replica_nodes),c.checksum)
    return StreamingResponse(stream(),media_type=obj.content_type,headers={'Content-Disposition':f'attachment; filename="{obj.filename}"'})
@app.delete('/files/{file_id}')
async def delete(file_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    obj=db.get(FileObject,file_id)
    if not obj or obj.owner_id!=user.id: raise HTTPException(404,'File not found')
    for v in db.scalars(select(FileVersion).where(FileVersion.file_id==file_id)).all():
        for c in db.scalars(select(Chunk).where(Chunk.version_id==v.id)).all():db.delete(c)
        db.delete(v)
    db.delete(obj);db.commit()
    try:await cache.delete(f'files:{user.id}')
    except:pass
    return {'status':'deleted'}
@app.post('/admin/rebalance')
async def rebalance(user:User=Depends(current_user),db:Session=Depends(get_db)):
    import httpx
    nodes=await healthy_nodes();repaired=0
    for c in db.scalars(select(Chunk)).all():
        current=json.loads(c.replica_nodes);good=[];source=None
        async with httpx.AsyncClient(timeout=10) as client:
            for n in current:
                try:
                    r=await client.get(f'{n}/chunks/{c.version_id}/{c.chunk_index}')
                    if r.status_code==200 and hashlib.sha256(r.content).hexdigest()==c.checksum:good.append(n);source=source or r.content
                except:pass
            if source:
                for target in [n for n in nodes if n not in good][:(max(0,RF-len(good)))]:
                    try:
                        r=await client.put(f'{target}/chunks/{c.version_id}/{c.chunk_index}',content=source,headers={'x-checksum':c.checksum});r.raise_for_status();good.append(target);repaired+=1
                    except:pass
        c.replica_nodes=json.dumps(good)
    db.commit();return {'status':'done','repaired_replicas':repaired,'healthy_nodes':nodes}
