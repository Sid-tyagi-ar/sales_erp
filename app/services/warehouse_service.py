from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import HTTPException, status
from app.schemas.warehouse import WarehouseCreateRequest, WarehouseUpdateRequest, WarehouseResponse
from app.db.firebase import get_db
from firebase_admin import firestore
from app.core.logger import get_logger
from app.core.audit import AuditService, AuditEvents

logger = get_logger(__name__)

class WarehouseService:
    async def create(self, tenant_id: str, data: WarehouseCreateRequest) -> WarehouseResponse:
        try:
            db = get_db()
            
            # 1. Generate deterministic id from code
            warehouse_id = f"{tenant_id}_warehouse_{data.code.lower()}"
            warehouse_ref = db.collection("tenants").document(tenant_id).collection("warehouses").document(warehouse_id)
            
            # 2. Check document exists
            doc = await warehouse_ref.get()
            if doc.exists:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "WAREHOUSE_ALREADY_EXISTS",
                        "message": f"Warehouse code {data.code} already exists for this tenant"
                    }
                )
            
            # 3. Build and write document
            warehouse_data = {
                "id": warehouse_id,
                "tenant_id": tenant_id,
                "name": data.name,
                "code": data.code.upper(), # Ensure code is uppercase in DB
                "city": data.city,
                "active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "created_by": "system"
            }
            await warehouse_ref.set(warehouse_data)
            
            # Log and Audit
            logger.info(f"[{tenant_id}] Warehouse created: {data.code}")
            audit_service = AuditService()
            await audit_service.log(
                tenant_id=tenant_id,
                event_type=AuditEvents.WAREHOUSE_CREATED,
                entity_type="warehouse",
                entity_id=warehouse_id,
                description=f"Warehouse created: {data.name} ({data.code})",
                metadata={"code": data.code, "city": data.city}
            )

            # 4. Return WarehouseResponse
            return WarehouseResponse(**warehouse_data)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating warehouse {data.code} for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def get(self, tenant_id: str, warehouse_id: str) -> WarehouseResponse:
        try:
            db = get_db()
            warehouse_ref = db.collection("tenants").document(tenant_id).collection("warehouses").document(warehouse_id)
            doc = await warehouse_ref.get()
            
            if not doc.exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "WAREHOUSE_NOT_FOUND",
                        "message": f"Warehouse {warehouse_id} not found"
                    }
                )
            
            return WarehouseResponse(**doc.to_dict())
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching warehouse {warehouse_id} for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def get_by_code(self, tenant_id: str, code: str) -> WarehouseResponse:
        try:
            # 1. Construct id
            warehouse_id = f"{tenant_id}_warehouse_{code.lower()}"
            # 2. Reuse get()
            return await self.get(tenant_id, warehouse_id)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching warehouse by code {code} for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def list(self, tenant_id: str) -> List[WarehouseResponse]:
        try:
            db = get_db()
            warehouses_ref = db.collection("tenants").document(tenant_id).collection("warehouses")
            docs = await warehouses_ref.get()
            
            return [WarehouseResponse(**doc.to_dict()) for doc in docs]
        except Exception as e:
            logger.error(f"Error listing warehouses for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def update(self, tenant_id: str, warehouse_id: str, data: WarehouseUpdateRequest) -> WarehouseResponse:
        try:
            db = get_db()
            
            # 1. Confirm exists via get()
            # This will raise HTTPException if not found
            await self.get(tenant_id, warehouse_id) 
            
            warehouse_ref = db.collection("tenants").document(tenant_id).collection("warehouses").document(warehouse_id)
            
            # 2. Build non-None fields dict
            update_data = data.model_dump(exclude_unset=True)
            
            # 3. Note: code is NOT updatable, ignore if somehow passed
            if "code" in update_data:
                del update_data["code"]

            # always add updated_at: datetime.utcnow()
            update_data["updated_at"] = datetime.utcnow()
            
            if not update_data:
                pass

            await warehouse_ref.update(update_data)
            
            # Log
            logger.info(f"[{tenant_id}] Warehouse updated: {warehouse_id}")

            # 4. Fetch and return updated WarehouseResponse
            updated_doc = await warehouse_ref.get()
            return WarehouseResponse(**updated_doc.to_dict())
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating warehouse {warehouse_id} for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def validate_active(self, tenant_id: str, warehouse_id: str) -> WarehouseResponse:
        try:
            # 1. Call get()
            warehouse = await self.get(tenant_id, warehouse_id)
            
            # 2. If warehouse.active is False raise HTTPException 400
            if not warehouse.active:
                logger.warning(f"[{tenant_id}] Inactive warehouse access attempted: {warehouse_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "WAREHOUSE_INACTIVE",
                        "message": f"Warehouse {warehouse_id} is inactive and cannot be used for stock movements"
                    }
                )
            
            # 3. Return warehouse
            return warehouse
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error validating active warehouse {warehouse_id} for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )
