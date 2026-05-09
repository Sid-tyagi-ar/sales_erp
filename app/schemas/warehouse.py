from typing import Optional
from pydantic import BaseModel, field_validator

class WarehouseCreateRequest(BaseModel):
    name: str
    code: str
    city: str

    @field_validator('code')
    @classmethod
    def code_to_uppercase(cls, v: str) -> str:
        return v.upper()

class WarehouseUpdateRequest(BaseModel):
    name: Optional[str] = None
    city: Optional[str] = None
    active: Optional[bool] = None

class WarehouseResponse(BaseModel):
    id: str
    name: str
    code: str
    city: str
    active: bool
