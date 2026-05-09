from datetime import datetime
from typing import Optional
from pydantic import field_validator
from app.models.base import TenantScopedBase
from app.enums import ManufacturingStatus

class ManufacturingOrder(TenantScopedBase):
    warehouse_id: str
    finished_good_id: str
    quantity_to_produce: float
    status: ManufacturingStatus = ManufacturingStatus.pending
    actual_cost: float = 0.0
    completed_at: Optional[datetime] = None

    @field_validator('quantity_to_produce')
    @classmethod
    def check_quantity_to_produce(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Quantity to produce must be greater than 0.")
        return v
