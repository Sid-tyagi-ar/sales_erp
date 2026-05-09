from pydantic import field_validator, Field
from app.models.base import TenantScopedBase

class BOMEntry(TenantScopedBase):
    finished_good_id: str
    raw_material_id: str
    quantity_required: float
    wastage_percent: float = Field(default=0.0, ge=0.0, le=100.0)

    @field_validator('quantity_required')
    @classmethod
    def check_quantity_required(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Quantity required must be greater than 0.")
        return v

    @property
    def effective_quantity(self) -> float:
        return self.quantity_required * (1 + self.wastage_percent / 100)
