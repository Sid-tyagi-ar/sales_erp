from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator
from app.models.base import TenantScopedBase
from app.enums import OrderStatus

class SalesOrderItem(BaseModel):
    product_id: str
    sku: str
    quantity: float
    unit_price: float
    dispatched_quantity: float = 0.0

    @property
    def line_total(self) -> float:
        return self.quantity * self.unit_price

class SalesOrder(TenantScopedBase):
    customer_id: str
    order_number: str
    status: OrderStatus = OrderStatus.draft
    items: List[SalesOrderItem]
    tax_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    subtotal: float = 0.0
    tax: float = 0.0
    grand_total: float = 0.0

    @model_validator(mode='after')
    def calculate_totals(self) -> 'SalesOrder':
        self.subtotal = sum(item.line_total for item in self.items)
        self.tax = self.subtotal * (self.tax_percent / 100)
        self.grand_total = self.subtotal + self.tax
        return self
