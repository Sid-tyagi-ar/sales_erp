from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.enums import ProductType, UnitOfMeasure

class ProductCreateRequest(BaseModel):
    name: str
    sku: str
    type: ProductType
    unit_of_measure: str # Corrected to str
    standard_cost: float = Field(ge=0.0)
    selling_price: float = Field(ge=0.0)
    sellable: bool = False

    @field_validator('sku')
    @classmethod
    def sku_to_uppercase(cls, v: str) -> str:
        return v.upper()

class ProductUpdateRequest(BaseModel):
    name: Optional[str] = None
    selling_price: Optional[float] = Field(default=None, ge=0.0)
    active: Optional[bool] = None
    sellable: Optional[bool] = None

class ProductResponse(BaseModel):
    id: str
    sku: str
    name: str
    type: ProductType
    unit_of_measure: str
    standard_cost: float
    selling_price: float
    active: bool
    sellable: bool
