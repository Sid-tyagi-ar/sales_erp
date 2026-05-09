from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.enums import ManufacturingStatus

class ManufacturingOrderRequest(BaseModel):
    warehouse_id: str
    finished_good_sku: str
    quantity_to_produce: float = Field(gt=0)

class ShortageItem(BaseModel):
    sku: str
    required: float
    available: float
    shortage: float

class ManufacturingOrderResponse(BaseModel):
    id: str
    warehouse_id: str
    finished_good_sku: str
    quantity_to_produce: float
    status: ManufacturingStatus
    actual_cost: float
    created_at: datetime

class ManufacturingCompleteResponse(BaseModel):
    success: bool
    can_complete: bool
    shortages: List[ShortageItem] = []
    ledger_entry_ids: List[str] = []
    actual_cost: float = 0.0
