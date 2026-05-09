from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional

class TenantCreateRequest(BaseModel):
    name: str
    email: EmailStr

class TenantUpdateRequest(BaseModel):
    name: Optional[str] = None

class TenantResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    created_at: datetime