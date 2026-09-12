from pydantic import BaseModel,EmailStr,Field
class RegisterIn(BaseModel): email:EmailStr; password:str=Field(min_length=8,max_length=128)
class LoginIn(BaseModel): email:EmailStr; password:str
class UploadStartIn(BaseModel): filename:str; size_bytes:int=Field(gt=0); content_type:str='application/octet-stream'; existing_file_id:int|None=None
class UploadCompleteIn(BaseModel): file_checksum:str|None=None
