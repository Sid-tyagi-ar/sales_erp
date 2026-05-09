from datetime import datetime
from pydantic import BaseModel
from app.enums import MovementType

class StockLedgerResponse(BaseModel):
    id: str
    product_sku: str
    warehouse_name: str
    movement_type: MovementType
    quantity_change: float
    unit_cost: float
    reference_type: str
    reference_id: str
    created_at: datetime
    created_by: str
