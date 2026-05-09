from typing import List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

class PurchaseReceiptItem(BaseModel):
    sku: str
    quantity: float = Field(gt=0)
    unit_cost: float = Field(gt=0)

class PurchaseReceiptRequest(BaseModel):
    warehouse_id: str
    items: List[PurchaseReceiptItem]

    @field_validator('items')
    @classmethod
    def items_not_empty(cls, v: List[PurchaseReceiptItem]) -> List[PurchaseReceiptItem]:
        if not v:
            raise ValueError("Purchase receipt must contain at least one item.")
        return v

class PurchaseReceiptResponse(BaseModel):
    id: str
    warehouse_id: str
    items: List[PurchaseReceiptItem]
    created_at: datetime
    ledger_entry_ids: List[str]
