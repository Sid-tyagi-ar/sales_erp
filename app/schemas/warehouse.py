from typing import Optional
from pydantic import BaseModel, field_validator, model_validator

class WarehouseCreateRequest(BaseModel):
    name: str
    code: str
    city: Optional[str] = None
    location: Optional[str] = None

    @field_validator('code')
    @classmethod
    def code_to_uppercase(cls, v: str) -> str:
        return v.upper()

    @model_validator(mode="after")
    def normalize_location(self):
        if not self.city and self.location:
            self.city = self.location
        return self

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