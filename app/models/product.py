from pydantic import Field, model_validator, field_validator
from typing import Optional
from app.models.base import TenantScopedBase
from app.enums import ProductType, UnitOfMeasure # Keep UnitOfMeasure for potential validation if needed

class Product(TenantScopedBase):
    name: str
    sku: str
    type: ProductType
    unit_of_measure: str # Corrected to str
    standard_cost: float
    selling_price: float
    active: bool = True
    sellable: bool = False

    @field_validator('sku')
    @classmethod
    def sku_to_uppercase(cls, v: str) -> str:
        return v.upper()

    @field_validator('standard_cost', 'selling_price')
    @classmethod
    def check_non_negative_prices(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Cost and selling price must be non-negative.")
        return v

    @model_validator(mode='after')
    def set_sellable_for_finished_good(self) -> 'Product':
        if self.type == ProductType.finished_good:
            self.sellable = True
        return self