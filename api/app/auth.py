import os,datetime as dt,jwt
from fastapi import Depends,HTTPException,Header
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from .db import get_db
from .models import User
pwd=CryptContext(schemes=['bcrypt'],deprecated='auto'); SECRET=os.getenv('JWT_SECRET','dev-secret')
def hash_password(p): return pwd.hash(p)
def verify_password(p,h): return pwd.verify(p,h)
def create_token(uid): return jwt.encode({'sub':str(uid),'exp':dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=24)},SECRET,algorithm='HS256')
def current_user(authorization:str|None=Header(default=None),db:Session=Depends(get_db)):
    if not authorization or not authorization.lower().startswith('bearer '): raise HTTPException(401,'Missing bearer token')
    try: uid=int(jwt.decode(authorization.split(' ',1)[1],SECRET,algorithms=['HS256'])['sub'])
    except Exception: raise HTTPException(401,'Invalid or expired token')
    user=db.get(User,uid)
    if not user: raise HTTPException(401,'User not found')
    return user
