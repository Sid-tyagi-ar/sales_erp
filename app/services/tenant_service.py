from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import HTTPException, status
from app.schemas.tenant import TenantCreateRequest, TenantResponse, TenantUpdateRequest
from app.db.firebase import get_db
from firebase_admin import firestore
from app.core.logger import get_logger
from app.core.audit import AuditService, AuditEvents

logger = get_logger(__name__)

class TenantService:
    async def create(self, data: TenantCreateRequest) -> TenantResponse:
        try:
            db = get_db()
            
            # 1. Generate deterministic id from email
            tenant_id = f"tenant_{data.email.lower().replace('@','_').replace('.','_')}"
            tenant_ref = db.collection("tenants").document(tenant_id)
            
            # 2. Check document exists
            doc = await tenant_ref.get()
            if doc.exists:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "TENANT_ALREADY_EXISTS",
                        "message": f"Tenant with email {data.email} already exists"
                    }
                )
            
            # 3. Build and write document
            tenant_data = {
                "id": tenant_id,
                "name": data.name,
                "email": data.email,
                "active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            await tenant_ref.set(tenant_data)
            
            # Log and Audit
            logger.info(f"[{tenant_id}] Tenant created: {data.email}")
            audit_service = AuditService()
            await audit_service.log(
                tenant_id=tenant_id,
                event_type=AuditEvents.TENANT_CREATED,
                entity_type="tenant",
                entity_id=tenant_id,
                description=f"Tenant created: {data.name}",
                metadata={"email": data.email}
            )

            # 4. Return TenantResponse
            return TenantResponse(**tenant_data)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating tenant {data.email}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def get(self, tenant_id: str) -> TenantResponse:
        try:
            db = get_db()
            logger.debug(f"Fetching tenant: {tenant_id}")
            tenant_ref = db.collection("tenants").document(tenant_id)
            doc = await tenant_ref.get()
            
            if not doc.exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "TENANT_NOT_FOUND",
                        "message": f"Tenant {tenant_id} not found"
                    }
                )
            
            return TenantResponse(**doc.to_dict())
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def list(self) -> List[TenantResponse]:
        try:
            db = get_db()
            tenants_ref = db.collection("tenants")
            
            # 1. Fetch all docs from /tenants
            # 2. Filter where active == True
            query = tenants_ref.where("active", "==", True)
            docs = await query.get()
            
            # 3. Return list[TenantResponse]
            return [TenantResponse(**doc.to_dict()) for doc in docs]
        except Exception as e:
            logger.error(f"Error listing tenants: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def update(self, tenant_id: str, data: TenantUpdateRequest) -> TenantResponse:
        try:
            db = get_db()
            
            # 1. Confirm exists via get()
            # This will raise HTTPException if not found
            await self.get(tenant_id) 
            
            tenant_ref = db.collection("tenants").document(tenant_id)
            
            # 2. Build dict of only non-None fields from data
            update_data = data.model_dump(exclude_unset=True)
            
            # always add updated_at: datetime.utcnow()
            update_data["updated_at"] = datetime.utcnow()
            
            if not update_data:
                pass

            await tenant_ref.update(update_data)
            
            # Log and Audit
            logger.info(f"[{tenant_id}] Tenant updated: {tenant_id}")
            # No specific audit event for generic tenant update, but could be added if needed.

            # 4. Fetch and return updated TenantResponse
            updated_doc = await tenant_ref.get()
            return TenantResponse(**updated_doc.to_dict())
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def delete(self, tenant_id: str) -> Dict[str, str]:
        try:
            db = get_db()
            
            # 1. Confirm exists via get()
            # This will raise HTTPException if not found
            await self.get(tenant_id)
            
            tenant_ref = db.collection("tenants").document(tenant_id)
            
            # 2. Soft delete: set active=False, updated_at=now
            # do NOT delete Firestore document
            await tenant_ref.update({
                "active": False,
                "updated_at": datetime.utcnow()
            })
            
            # Log
            logger.info(f"[{tenant_id}] Tenant soft deleted")

            # 3. Return {"message": "Tenant deactivated successfully"}
            return {"message": "Tenant deactivated successfully"}
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )
