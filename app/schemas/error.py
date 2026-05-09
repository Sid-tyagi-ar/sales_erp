from typing import Optional, List
from pydantic import BaseModel

class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str

class ErrorResponse(BaseModel):
    error: str
    message: str
    details: List[ErrorDetail] = []
