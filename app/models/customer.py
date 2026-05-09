from typing import Optional
from app.models.base import TenantScopedBase

class Customer(TenantScopedBase):
    name: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
