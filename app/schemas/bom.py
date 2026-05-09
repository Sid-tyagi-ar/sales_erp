from typing import List
from pydantic import BaseModel, Field, field_validator

class BOMEntryRequest(BaseModel):
    raw_material_sku: str
    quantity_required: float = Field(gt=0)
    wastage_percent: float = Field(default=0.0, ge=0.0, le=100.0)

class BOMCreateRequest(BaseModel):
    finished_good_sku: str
    components: List[BOMEntryRequest]

    @field_validator('components')
    @classmethod
    def components_not_empty(cls, v: List[BOMEntryRequest]) -> List[BOMEntryRequest]:
        if not v:
            raise ValueError("BOM must contain at least one component.")
        return v

class BOMEntryResponse(BaseModel):
    raw_material_sku: str
    raw_material_name: str
    quantity_required: float
    wastage_percent: float
    effective_quantity: float

class BOMResponse(BaseModel):
    finished_good_sku: str
    finished_good_name: str
    components: List[BOMEntryResponse]
