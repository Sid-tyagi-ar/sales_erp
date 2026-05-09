from typing import List, Dict, Any
from datetime import datetime
from pydantic import BaseModel

class AuditEntryResponse(BaseModel):
    id: str
    event_type: str
    entity_type: str
    entity_id: str
    description: str
    metadata: Dict[str, Any]
    performed_by: str
    created_at: datetime
