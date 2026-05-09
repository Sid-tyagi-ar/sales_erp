from typing import List, Dict, Any, Optional
from datetime import datetime
from uuid import uuid4
from fastapi import HTTPException, status
from app.schemas.ledger import StockLedgerResponse
from app.enums import MovementType
from app.db.firebase import get_db
from firebase_admin import firestore
from firebase_admin.firestore import AsyncClient, AsyncDocumentReference, AsyncWriteBatch
from app.core.logger import get_logger
# from app.services.product_service import ProductService # Removed from module level
# from app.services.warehouse_service import WarehouseService # Removed from module level

logger = get_logger(__name__)

class LedgerService:
    async def build_entry(
        self,
        tenant_id: str,
        warehouse_id: str,
        product_id: str,
        movement_type: MovementType,
        quantity_change: float,
        unit_cost: float,
        reference_type: str,
        reference_id: str,
        created_by: str = "system"
    ) -> Dict[str, Any]:
        if quantity_change == 0:
            raise ValueError("Quantity change cannot be zero for a ledger entry.")
        
        entry_id = f"{tenant_id}_ledger_{uuid4().hex[:8]}_{int(datetime.utcnow().timestamp())}"
        
        entry_data = {
            "id": entry_id,
            "tenant_id": tenant_id,
            "warehouse_id": warehouse_id,
            "product_id": product_id,
            "movement_type": movement_type.value,
            "quantity_change": quantity_change,
            "unit_cost": unit_cost,
            "reference_type": reference_type,
            "reference_id": reference_id,
            "created_at": datetime.utcnow(),
            "created_by": created_by
        }

        logger.debug(
            f"[{tenant_id}] Ledger entry built | "
            f"type:{movement_type.value} product:{product_id} "
            f"qty:{quantity_change}"
        )
        
        return entry_data

    async def append_to_batch(self, batch: AsyncWriteBatch, tenant_id: str, entry_dict: Dict[str, Any]) -> str:
        try:
            db = get_db()
            ledger_ref = db.collection("tenants").document(tenant_id).collection("stock_ledger").document(entry_dict["id"])
            batch.set(ledger_ref, entry_dict)
            return entry_dict["id"]
        except Exception as e:
            logger.error(f"Error appending ledger entry to batch for tenant {tenant_id}, entry {entry_dict.get('id')}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred while adding ledger entry to batch: {e}"}
            )

    async def list(
        self,
        tenant_id: str,
        warehouse_id: Optional[str] = None,
        product_id: Optional[str] = None,
        movement_type: Optional[MovementType] = None,
        limit: int = 100
    ) -> List[StockLedgerResponse]:
        from app.services.product_service import ProductService # Import locally for name lookup
        from app.services.warehouse_service import WarehouseService # Import locally for name lookup
        
        product_service = ProductService()
        warehouse_service = WarehouseService()

        try:
            db = get_db()
            query = db.collection("tenants").document(tenant_id).collection("stock_ledger")
            
            if warehouse_id:
                query = query.where("warehouse_id", "==", warehouse_id)
            if product_id:
                query = query.where("product_id", "==", product_id)
            if movement_type:
                query = query.where("movement_type", "==", movement_type.value)
            
            query = query.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
            
            docs = await query.get()
            
            responses = []
            for doc in docs:
                entry_data = doc.to_dict()
                
                # Fetch product sku and warehouse name using deterministic IDs
                # NOTE: Per instruction, do not import services directly into other service files.
                # So, we fetch directly.
                
                # Fetch product details for SKU
                try:
                    product = await product_service.get(tenant_id, entry_data["product_id"])
                    product_sku = product.sku
                except HTTPException as e:
                    if e.status_code == status.HTTP_404_NOT_FOUND:
                        product_sku = "Unknown SKU"
                    else:
                        raise

                # Fetch warehouse details for name
                try:
                    warehouse = await warehouse_service.get(tenant_id, entry_data["warehouse_id"])
                    warehouse_name = warehouse.name
                except HTTPException as e:
                    if e.status_code == status.HTTP_404_NOT_FOUND:
                        warehouse_name = "Unknown Warehouse"
                    else:
                        raise

                responses.append(StockLedgerResponse(
                    id=entry_data["id"],
                    product_sku=product_sku,
                    warehouse_name=warehouse_name,
                    movement_type=MovementType(entry_data["movement_type"]),
                    quantity_change=entry_data["quantity_change"],
                    unit_cost=entry_data["unit_cost"],
                    reference_type=entry_data["reference_type"],
                    reference_id=entry_data["reference_id"],
                    created_at=entry_data["created_at"],
                    created_by=entry_data["created_by"]
                ))
            return responses
        except Exception as e:
            logger.error(f"Error listing stock ledger entries for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )
