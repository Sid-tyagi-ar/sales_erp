import logging
from datetime import datetime
from uuid import uuid4
from typing import Dict, Any
from app.db.firebase import get_db
from firebase_admin import firestore
from app.core.logger import get_logger

logger = get_logger(__name__)

# Event types to use as constants
class AuditEvents:
    PRODUCT_CREATED = "PRODUCT_CREATED"
    PRODUCT_UPDATED = "PRODUCT_UPDATED"
    WAREHOUSE_CREATED = "WAREHOUSE_CREATED"
    STOCK_RECEIVED = "STOCK_RECEIVED"
    BOM_CREATED = "BOM_CREATED"
    MANUFACTURING_CREATED = "MANUFACTURING_CREATED"
    MANUFACTURING_COMPLETED = "MANUFACTURING_COMPLETED"
    SALES_ORDER_CREATED = "SALES_ORDER_CREATED"
    SALES_ORDER_CONFIRMED = "SALES_ORDER_CONFIRMED"
    STOCK_RESERVED = "STOCK_RESERVED"
    STOCK_DISPATCHED = "STOCK_DISPATCHED"
    RESERVATION_RELEASED = "RESERVATION_RELEASED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    TENANT_CREATED = "TENANT_CREATED"

class AuditService:
    async def log(
        self,
        tenant_id: str,
        event_type: str,
        entity_type: str,
        entity_id: str,
        description: str,
        metadata: Dict = {},
        performed_by: str = "system"
    ) -> None:
        try:
            db = get_db()
            
            # 1. Build audit document
            audit_id = f"{tenant_id}_audit_{uuid4().hex[:8]}_{int(datetime.utcnow().timestamp())}"
            audit_data = {
                "id": audit_id,
                "tenant_id": tenant_id,
                "event_type": event_type,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "description": description,
                "metadata": metadata,
                "performed_by": performed_by,
                "created_at": datetime.utcnow()
            }
            
            # 2. Write to Firestore (standalone write, no batch needed)
            audit_ref = db.collection("tenants").document(tenant_id).collection("audit_log").document(audit_id)
            await audit_ref.set(audit_data)
            
            # 3. Also log to Python logger
            logger.info(
                f"[{tenant_id}] AUDIT | {event_type} | "
                f"{entity_type}:{entity_id} | {description}"
            )
        except Exception as e:
            # 4. Audit failure must NEVER crash the main operation. Silently log the error and continue.
            logger.error(f"Audit log failed for tenant {tenant_id}, event {event_type}, entity {entity_id}: {e}")
