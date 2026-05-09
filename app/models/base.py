from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any
import uuid

class TenantScopedBase(BaseModel):
    id: Optional[str] = None
    tenant_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = "system"
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def generate_id(cls, *parts: str) -> str:
        """Generates a deterministic ID based on provided parts."""
        return "_".join(parts).lower()

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        from_attributes=True # Allow initialization from ORM attributes
    )