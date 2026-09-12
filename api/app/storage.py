import os,hashlib,asyncio,httpx
from fastapi import HTTPException
NODES=[n.rstrip('/') for n in os.getenv('STORAGE_NODES','http://storage-a:9000,http://storage-b:9000,http://storage-c:9000').split(',') if n.strip()]
RF=max(1,int(os.getenv('REPLICATION_FACTOR','2')))
async def healthy_nodes():
    async with httpx.AsyncClient(timeout=2) as c:
        async def ping(n):
            try:return n if (await c.get(n+'/health')).status_code==200 else None
            except:return None
        r=await asyncio.gather(*(ping(n) for n in NODES))
    return [x for x in r if x]
async def put_chunk(version_id,index,data):
    nodes=await healthy_nodes()
    if len(nodes)<RF: raise HTTPException(503,f'Need {RF} healthy nodes; only {len(nodes)} available')
    start=index%len(nodes); targets=(nodes[start:]+nodes[:start])[:RF]; digest=hashlib.sha256(data).hexdigest()
    async with httpx.AsyncClient(timeout=30) as c:
        async def write(n):
            r=await c.put(f'{n}/chunks/{version_id}/{index}',content=data,headers={'x-checksum':digest}); r.raise_for_status()
        await asyncio.gather(*(write(n) for n in targets))
    return digest,targets
async def get_chunk(version_id,index,nodes,checksum):
    async with httpx.AsyncClient(timeout=20) as c:
        for n in nodes:
            try:
                r=await c.get(f'{n}/chunks/{version_id}/{index}')
                if r.status_code==200 and hashlib.sha256(r.content).hexdigest()==checksum:return r.content
            except:pass
    raise HTTPException(503,f'No healthy replica for chunk {index}')
