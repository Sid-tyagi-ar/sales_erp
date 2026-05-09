from typing import Optional
from pydantic import BaseModel, EmailStr

class CustomerCreateRequest(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None

class CustomerResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
