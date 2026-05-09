from pydantic import field_validator
from app.models.base import TenantScopedBase
from app.enums import MovementType

class StockLedgerEntry(TenantScopedBase):
    warehouse_id: str
    product_id: str
    movement_type: MovementType
    quantity_change: float
    unit_cost: float
    reference_type: str
    reference_id: str

    @field_validator('quantity_change')
    @classmethod
    def check_quantity_change(cls, v: float) -> float:
        if v == 0:
            raise ValueError("Quantity change cannot be zero.")
        return v
