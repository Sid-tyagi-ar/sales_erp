from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from app.enums import OrderStatus

class SalesOrderItemRequest(BaseModel):
    sku: str
    quantity: float = Field(gt=0)

class SalesOrderCreateRequest(BaseModel):
    customer_id: str
    order_number: str
    items: List[SalesOrderItemRequest]
    tax_percent: float = Field(default=0.0, ge=0.0, le=100.0)

    @field_validator('items')
    @classmethod
    def items_not_empty(cls, v: List[SalesOrderItemRequest]) -> List[SalesOrderItemRequest]:
        if not v:
            raise ValueError("Sales order must contain at least one item.")
        return v

class DispatchItem(BaseModel):
    sku: str
    quantity: float = Field(gt=0)

class DispatchRequest(BaseModel):
    items: List[DispatchItem]

class SalesOrderItemResponse(BaseModel):
    sku: str
    product_name: str
    quantity: float
    unit_price: float
    dispatched_quantity: float
    line_total: float

class SalesOrderResponse(BaseModel):
    id: str
    order_number: str
    customer_id: str
    customer_name: str
    status: OrderStatus
    items: List[SalesOrderItemResponse]
    subtotal: float
    tax: float
    grand_total: float
    created_at: datetime
