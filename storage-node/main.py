import os,hashlib
from pathlib import Path
from fastapi import FastAPI,Request,HTTPException
from fastapi.responses import FileResponse
app=FastAPI(title='Storage Node')
NODE_NAME=os.getenv('NODE_NAME','storage-node');ROOT=Path(os.getenv('STORAGE_PATH','/data'));ROOT.mkdir(parents=True,exist_ok=True)
def path(v,i):return ROOT/str(v)/f'{i}.chunk'
@app.get('/health')
def health():return {'status':'ok','node':NODE_NAME}
@app.put('/chunks/{version_id}/{chunk_index}')
async def put(version_id:int,chunk_index:int,request:Request):
    data=await request.body();expected=request.headers.get('x-checksum');actual=hashlib.sha256(data).hexdigest()
    if expected and expected!=actual:raise HTTPException(400,'Checksum mismatch')
    p=path(version_id,chunk_index);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.tmp');tmp.write_bytes(data);tmp.replace(p);return {'status':'stored','node':NODE_NAME,'bytes':len(data),'checksum':actual}
@app.get('/chunks/{version_id}/{chunk_index}')
def get(version_id:int,chunk_index:int):
    p=path(version_id,chunk_index)
    if not p.exists():raise HTTPException(404,'Chunk not found')
    return FileResponse(p,media_type='application/octet-stream')
@app.delete('/chunks/{version_id}/{chunk_index}')
def delete(version_id:int,chunk_index:int):
    p=path(version_id,chunk_index)
    if p.exists():p.unlink()
    return {'status':'deleted','node':NODE_NAME}
