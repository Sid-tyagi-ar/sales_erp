from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import HTTPException, status
from app.schemas.manufacturing_order import ManufacturingOrderRequest, ManufacturingOrderResponse, ManufacturingCompleteResponse, ShortageItem
from app.schemas.product import ProductResponse
from app.schemas.error import ErrorDetail
from app.enums import ManufacturingStatus, ProductType, MovementType
from app.db.firebase import get_db
from firebase_admin import firestore
from app.core.logger import get_logger
from app.core.audit import AuditService, AuditEvents
# from app.services.warehouse_service import WarehouseService # Removed from module level
# from app.services.product_service import ProductService # Removed from module level
# from app.services.bom_service import BOMService # Removed from module level
# from app.services.inventory_service import InventoryService # Removed from module level
# from app.services.ledger_service import LedgerService # Removed from module level
from uuid import uuid4

logger = get_logger(__name__)

class ManufacturingService:
    async def get(self, tenant_id: str, order_id: str) -> ManufacturingOrderResponse:
        try:
            db = get_db()
            order_ref = db.collection("tenants").document(tenant_id).collection("manufacturing_orders").document(order_id)
            doc = await order_ref.get()
            
            if not doc.exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "ORDER_NOT_FOUND",
                        "message": f"Manufacturing Order {order_id} not found"
                    }
                )
            
            return ManufacturingOrderResponse(**doc.to_dict())
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting manufacturing order {order_id} for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def create_order(self, tenant_id: str, data: ManufacturingOrderRequest) -> ManufacturingOrderResponse:
        from app.services.warehouse_service import WarehouseService # Import locally
        from app.services.product_service import ProductService # Import locally
        from app.services.bom_service import BOMService # Import locally
        
        warehouse_service = WarehouseService()
        product_service = ProductService()
        bom_service = BOMService()

        try:
            db = get_db()
            
            # Step 1: Validate warehouse active
            await warehouse_service.validate_active(tenant_id, data.warehouse_id)
            
            # Step 2: Validate finished good
            finished_good_product: ProductResponse = await product_service.get_by_sku(tenant_id, data.finished_good_sku)
            if finished_good_product.type != ProductType.finished_good:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "INVALID_PRODUCT_TYPE",
                        "message": "Only finished goods can be manufactured"
                    }
                )
            
            # Step 3: Validate BOM exists
            bom = await bom_service.get_bom_for_product(tenant_id, finished_good_product.id)
            if not bom:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "BOM_NOT_DEFINED",
                        "message": f"No BOM defined for {data.finished_good_sku}. Define a BOM before manufacturing."
                    }
                )
            
            # Step 4: Write manufacturing order document
            manufacturing_order_id = f"{tenant_id}_mfg_{uuid4().hex[:8]}"
            order_data = {
                "id": manufacturing_order_id,
                "tenant_id": tenant_id,
                "warehouse_id": data.warehouse_id,
                "finished_good_id": finished_good_product.id, # This is now explicitly saved
                "finished_good_sku": finished_good_product.sku,
                "quantity_to_produce": data.quantity_to_produce,
                "status": ManufacturingStatus.pending.value,
                "actual_cost": 0.0,
                "completed_at": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "created_by": "system"
            }
            order_ref = db.collection("tenants").document(tenant_id).collection("manufacturing_orders").document(manufacturing_order_id)
            await order_ref.set(order_data)
            
            # Log
            logger.info(
                f"[{tenant_id}] Manufacturing order created | "
                f"product:{data.finished_good_sku} "
                f"qty:{data.quantity_to_produce}"
            )

            # 5. Return ManufacturingOrderResponse
            return ManufacturingOrderResponse(**order_data)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating manufacturing order for tenant {tenant_id}, product {data.finished_good_sku}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def complete_order(self, tenant_id: str, order_id: str) -> ManufacturingCompleteResponse:
        from app.services.bom_service import BOMService # Import locally
        from app.services.inventory_service import InventoryService # Import locally
        from app.services.ledger_service import LedgerService # Import locally
        
        bom_service = BOMService()
        inventory_service = InventoryService()
        ledger_service = LedgerService()

        try:
            db = get_db()
            
            # Step 1: Fetch manufacturing order
            order_doc = await self.get(tenant_id, order_id) # This will raise 404 if not found
            order_data = order_doc.model_dump() # This converts ManufacturingOrderResponse to dict
            
            # DEBUG print to check keys
            print(f"DEBUG: complete_order - order_data keys: {list(order_data.keys())}")

            if order_data["status"] != ManufacturingStatus.pending.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "ORDER_ALREADY_PROCESSED",
                        "message": f"Order is already {order_data['status']}"
                    }
                )
            
            # Step 2: Fetch BOM for finished good
            bom_entries = await bom_service.get_bom_for_product(tenant_id, order_data["finished_good_id"]) # Accesses finished_good_id
            if not bom_entries:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "BOM_NOT_DEFINED",
                        "message": f"No BOM defined for {order_data['finished_good_sku']}. Cannot complete manufacturing."
                    }
                )
            
            # Step 3: Check availability for ALL components first
            shortages: List[ShortageItem] = []
            component_data: List[Dict[str, Any]] = []
            
            for bom_entry in bom_entries:
                required_qty = bom_entry["effective_quantity"] * order_data["quantity_to_produce"]
                
                balance = await inventory_service.get_balance(
                    tenant_id, order_data["warehouse_id"], bom_entry["raw_material_id"]
                )
                
                available = balance["on_hand_quantity"] - balance["reserved_quantity"]
                
                if available < required_qty:
                    shortages.append(ShortageItem(
                        sku=bom_entry["raw_material_sku"],
                        required=required_qty,
                        available=available,
                        shortage=required_qty - available
                    ))
                else:
                    component_data.append({
                        "product_id": bom_entry["raw_material_id"],
                        "sku": bom_entry["raw_material_sku"],
                        "required_qty": required_qty,
                        "unit_cost": balance["average_cost"]
                    })
            
            if shortages:
                logger.warning(
                    f"[{tenant_id}] Manufacturing cannot complete | "
                    f"order:{order_id} shortages:{len(shortages)}"
                )
                return ManufacturingCompleteResponse(
                    success=False,
                    can_complete=False,
                    shortages=shortages
                )
            
            # Step 4: All available — calculate finished good cost
            total_material_cost = sum(
                component["required_qty"] * component["unit_cost"]
                for component in component_data
            )
            finished_good_unit_cost = (total_material_cost / order_data["quantity_to_produce"]) if order_data["quantity_to_produce"] > 0 else 0.0

            # Step 5: Build batch — everything or nothing
            batch = db.batch()
            ledger_entry_ids = []
            
            # a. For each component issue raw materials
            for component in component_data:
                # Issue reduces on_hand only (not reserved since manufacturing doesn't reserve first)
                await inventory_service.issue_for_manufacturing(
                    tenant_id=tenant_id,
                    warehouse_id=order_data["warehouse_id"],
                    product_id=component["product_id"],
                    quantity=component["required_qty"],
                    batch_or_transaction=batch
                )
                
                entry_dict = await ledger_service.build_entry(
                    tenant_id=tenant_id,
                    warehouse_id=order_data["warehouse_id"],
                    product_id=component["product_id"],
                    movement_type=MovementType.manufacturing_issue,
                    quantity_change=-component["required_qty"],
                    unit_cost=component["unit_cost"],
                    reference_type="manufacturing_order",
                    reference_id=order_id
                )
                ledger_id = await ledger_service.append_to_batch(batch, tenant_id, entry_dict)
                ledger_entry_ids.append(ledger_id)
            
            # b. Receive finished good into inventory
            await inventory_service.update_on_receipt(
                tenant_id=tenant_id,
                warehouse_id=order_data["warehouse_id"],
                product_id=order_data["finished_good_id"],
                quantity=order_data["quantity_to_produce"],
                unit_cost=finished_good_unit_cost,
                batch_or_transaction=batch
            )
            
            fg_entry_dict = await ledger_service.build_entry(
                tenant_id=tenant_id,
                warehouse_id=order_data["warehouse_id"],
                product_id=order_data["finished_good_id"],
                movement_type=MovementType.manufacturing_receipt,
                quantity_change=order_data["quantity_to_produce"],
                unit_cost=finished_good_unit_cost,
                reference_type="manufacturing_order",
                reference_id=order_id
            )
            fg_ledger_id = await ledger_service.append_to_batch(batch, tenant_id, fg_entry_dict)
            ledger_entry_ids.append(fg_ledger_id)
            
            # c. Update manufacturing order status
            order_ref = db.collection("tenants").document(tenant_id).collection("manufacturing_orders").document(order_id)
            batch.update(order_ref, {
                "status": ManufacturingStatus.completed.value,
                "actual_cost": total_material_cost,
                "completed_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            
            # d. Commit batch
            await batch.commit()

            # Log and Audit
            logger.info(
                f"[{tenant_id}] Manufacturing completed | "
                f"order:{order_id} cost:{total_material_cost:.2f}"
            )
            audit_service = AuditService()
            await audit_service.log(
                tenant_id=tenant_id,
                event_type=AuditEvents.MANUFACTURING_COMPLETED,
                entity_type="manufacturing_order",
                entity_id=order_id,
                description=f"Manufacturing order completed for {order_data['finished_good_sku']}",
                metadata={
                    "finished_good_id": order_data["finished_good_id"],
                    "quantity_produced": order_data["quantity_to_produce"],
                    "actual_cost": total_material_cost
                }
            )

            # Step 6: Return ManufacturingCompleteResponse
            return ManufacturingCompleteResponse(
                success=True,
                can_complete=True,
                shortages=[],
                ledger_entry_ids=ledger_entry_ids,
                actual_cost=total_material_cost
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error completing manufacturing order {order_id} for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )