from typing import List, Dict, Any
from datetime import datetime
from fastapi import HTTPException, status
from app.schemas.purchase_receipt import PurchaseReceiptRequest, PurchaseReceiptResponse
from app.schemas.error import ErrorDetail
from app.schemas.product import ProductResponse
from app.enums import MovementType, ProductType
from app.db.firebase import get_db
from firebase_admin import firestore
from app.core.logger import get_logger
from app.core.audit import AuditService, AuditEvents
# from app.services.warehouse_service import WarehouseService # Removed from module level
# from app.services.product_service import ProductService # Removed from module level
# from app.services.inventory_service import InventoryService # Removed from module level
# from app.services.ledger_service import LedgerService # Removed from module level
from uuid import uuid4

logger = get_logger(__name__)

class PurchaseReceiptService:
    async def create(self, tenant_id: str, data: PurchaseReceiptRequest) -> PurchaseReceiptResponse:
        from app.services.warehouse_service import WarehouseService # Import locally
        from app.services.product_service import ProductService # Import locally
        from app.services.inventory_service import InventoryService # Import locally
        from app.services.ledger_service import LedgerService # Import locally
        
        warehouse_service = WarehouseService()
        product_service = ProductService()
        inventory_service = InventoryService()
        ledger_service = LedgerService()

        try:
            db = get_db()
            errors: List[ErrorDetail] = []
            
            # Step 1: Validate warehouse
            try:
                await warehouse_service.validate_active(tenant_id, data.warehouse_id)
            except HTTPException as e:
                if e.status_code == status.HTTP_400_BAD_REQUEST:
                    errors.append(ErrorDetail(
                        field="warehouse_id",
                        message=f"Warehouse {data.warehouse_id} is inactive and cannot be used"
                    ))
                else:
                    raise # Re-raise other HTTP exceptions
            
            # Step 2: Validate all items before writing any
            validated_products: Dict[str, ProductResponse] = {}
            for item in data.items:
                try:
                    product = await product_service.get_by_sku(tenant_id, item.sku)
                    validated_products[item.sku] = product

                    # b. Check product type: if type == finished_good
                    if product.type == ProductType.finished_good:
                        errors.append(ErrorDetail(
                            field=f"items.{item.sku}",
                            message=f"{item.sku} is a finished good. Finished goods cannot be purchased, they are manufactured. Use a manufacturing order instead."
                        ))
                    
                    # c. Check product active
                    if not product.active:
                        errors.append(ErrorDetail(
                            field=f"items.{item.sku}",
                            message=f"Product {item.sku} is inactive and cannot be used"
                        ))
                except HTTPException as e:
                    if e.status_code == status.HTTP_404_NOT_FOUND:
                        errors.append(ErrorDetail(
                            field=f"items.{item.sku}",
                            message=f"Product {item.sku} not found"
                        ))
                    else:
                        raise # Re-raise other HTTP exceptions
            
            if errors:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "PURCHASE_RECEIPT_VALIDATION_FAILED",
                        "message": "One or more items failed validation",
                        "details": [e.model_dump() for e in errors]
                    }
                )

            # Step 3: All valid — build batch
            batch = db.batch()
            ledger_entry_ids = []
            receipt_items_for_response = []
            
            purchase_receipt_id = f"{tenant_id}_receipt_{uuid4().hex[:8]}"
            
            for item in data.items:
                product = validated_products[item.sku]
                
                # d. Add balance update to batch
                await inventory_service.update_on_receipt(
                    tenant_id=tenant_id,
                    warehouse_id=data.warehouse_id,
                    product_id=product.id,
                    quantity=item.quantity,
                    unit_cost=item.unit_cost,
                    batch_or_transaction=batch
                )
                
                # e. Build ledger entry
                ledger_entry_dict = await ledger_service.build_entry(
                    tenant_id=tenant_id,
                    warehouse_id=data.warehouse_id,
                    product_id=product.id,
                    movement_type=MovementType.purchase_receipt,
                    quantity_change=item.quantity,
                    unit_cost=item.unit_cost,
                    reference_type="purchase_receipt",
                    reference_id=purchase_receipt_id
                )
                
                # f. Add ledger entry to batch
                ledger_id = await ledger_service.append_to_batch(batch, tenant_id, ledger_entry_dict)
                ledger_entry_ids.append(ledger_id)

                # g. Append to receipt_items for response
                receipt_items_for_response.append(item.model_dump())

                logger.debug(
                    f"[{tenant_id}] Received | sku:{item.sku} "
                    f"qty:{item.quantity} cost:{item.unit_cost}"
                )
            
            # Step 4: Add receipt document to batch
            purchase_receipt_data = {
                "id": purchase_receipt_id,
                "tenant_id": tenant_id,
                "warehouse_id": data.warehouse_id,
                "items": receipt_items_for_response,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "created_by": "system",
                "ledger_entry_ids": ledger_entry_ids
            }
            pr_ref = db.collection("tenants").document(tenant_id).collection("purchase_receipts").document(purchase_receipt_id)
            batch.set(pr_ref, purchase_receipt_data)
            
            # Step 5: Commit batch
            await batch.commit()
            
            # Log and Audit
            logger.info(
                f"[{tenant_id}] Purchase receipt created | "
                f"warehouse:{data.warehouse_id} "
                f"items:{len(data.items)}"
            )
            audit_service = AuditService()
            await audit_service.log(
                tenant_id=tenant_id,
                event_type=AuditEvents.STOCK_RECEIVED,
                entity_type="purchase_receipt",
                entity_id=purchase_receipt_id,
                description=f"Stock received at warehouse {data.warehouse_id}",
                metadata={
                    "warehouse_id": data.warehouse_id,
                    "item_count": len(data.items),
                    "ledger_entry_ids": ledger_entry_ids
                }
            )

            # Step 6: Return PurchaseReceiptResponse
            return PurchaseReceiptResponse(**purchase_receipt_data)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating purchase receipt for tenant {tenant_id}, warehouse {data.warehouse_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )