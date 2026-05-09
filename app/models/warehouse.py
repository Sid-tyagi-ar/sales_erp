from pydantic import field_validator
from app.models.base import TenantScopedBase

class Warehouse(TenantScopedBase):
    name: str
    code: str
    city: str
    active: bool = True

    @field_validator('code')
    @classmethod
    def code_to_uppercase(cls, v: str) -> str:
        return v.upper()
