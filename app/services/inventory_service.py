from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import HTTPException, status
from app.schemas.inventory import InventoryBalanceResponse
from app.enums import MovementType
from app.db.firebase import get_db
from firebase_admin import firestore
from firebase_admin.firestore import AsyncClient, AsyncDocumentReference, AsyncTransaction, AsyncWriteBatch
from app.core.logger import get_logger

logger = get_logger(__name__)

class InventoryService:
    async def get_balance(self, tenant_id: str, warehouse_id: str, product_id: str, transaction: Optional[AsyncTransaction] = None) -> Dict[str, Any]:
        try:
            db = get_db()
            
            balance_id = f"{tenant_id}_balance_{warehouse_id}_{product_id}"
            balance_ref = db.collection("tenants").document(tenant_id).collection("inventory_balances").document(balance_id)
            
            doc = await balance_ref.get(transaction=transaction) if transaction else await balance_ref.get()
            
            if not doc.exists:
                return {
                    "id": balance_id,
                    "tenant_id": tenant_id,
                    "warehouse_id": warehouse_id,
                    "product_id": product_id,
                    "on_hand_quantity": 0.0,
                    "reserved_quantity": 0.0,
                    "average_cost": 0.0,
                    "updated_at": datetime.utcnow()
                }
            
            return doc.to_dict()
        except Exception as e:
            logger.error(f"Error getting inventory balance for tenant {tenant_id}, warehouse {warehouse_id}, product {product_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def list(self, tenant_id: str) -> List[InventoryBalanceResponse]:
        from app.services.product_service import ProductService # Import locally for name lookup
        from app.services.warehouse_service import WarehouseService # Import locally for name lookup
        
        product_service = ProductService()
        warehouse_service = WarehouseService()

        try:
            db = get_db()
            balances_ref = db.collection("tenants").document(tenant_id).collection("inventory_balances")
            docs = await balances_ref.get()
            
            responses = []
            for doc in docs:
                balance_data = doc.to_dict()
                
                product_id = balance_data["product_id"]
                warehouse_id = balance_data["warehouse_id"]

                # Fetch product details
                try:
                    product = await product_service.get(tenant_id, product_id)
                    product_name = product.name
                    product_sku = product.sku
                except HTTPException as e:
                    if e.status_code == status.HTTP_404_NOT_FOUND:
                        product_name = "Unknown Product"
                        product_sku = "Unknown SKU"
                    else:
                        raise

                # Fetch warehouse details
                try:
                    warehouse = await warehouse_service.get(tenant_id, warehouse_id)
                    warehouse_name = warehouse.name
                except HTTPException as e:
                    if e.status_code == status.HTTP_404_NOT_FOUND:
                        warehouse_name = "Unknown Warehouse"
                    else:
                        raise

                on_hand_quantity = balance_data.get("on_hand_quantity", 0.0)
                reserved_quantity = balance_data.get("reserved_quantity", 0.0)
                average_cost = balance_data.get("average_cost", 0.0)

                responses.append(InventoryBalanceResponse(
                    product_id=product_id,
                    sku=product_sku,
                    product_name=product_name,
                    warehouse_id=warehouse_id,
                    warehouse_name=warehouse_name,
                    on_hand_quantity=on_hand_quantity,
                    reserved_quantity=reserved_quantity,
                    available_quantity=on_hand_quantity - reserved_quantity,
                    average_cost=average_cost,
                    inventory_value=on_hand_quantity * average_cost
                ))
            return responses
        except Exception as e:
            logger.error(f"Error listing inventory balances for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def update_on_receipt(self, tenant_id: str, warehouse_id: str, product_id: str, quantity: float, unit_cost: float, batch_or_transaction: Any) -> Dict[str, Any]:
        try:
            db = get_db()
            balance_id = f"{tenant_id}_balance_{warehouse_id}_{product_id}"
            balance_ref = db.collection("tenants").document(tenant_id).collection("inventory_balances").document(balance_id)
            
            current_balance = await self.get_balance(tenant_id, warehouse_id, product_id, transaction=batch_or_transaction if isinstance(batch_or_transaction, AsyncTransaction) else None)

            current_on_hand = current_balance.get("on_hand_quantity", 0.0)
            current_avg_cost = current_balance.get("average_cost", 0.0)

            if current_on_hand == 0:
                new_avg_cost = unit_cost
            else:
                new_avg_cost = (
                    (current_on_hand * current_avg_cost) + 
                    (quantity * unit_cost)
                ) / (current_on_hand + quantity)
            
            updated_on_hand = current_on_hand + quantity
            
            update_data = {
                "id": balance_id,
                "tenant_id": tenant_id,
                "warehouse_id": warehouse_id,
                "product_id": product_id,
                "on_hand_quantity": updated_on_hand,
                "reserved_quantity": current_balance.get("reserved_quantity", 0.0),
                "average_cost": new_avg_cost,
                "updated_at": datetime.utcnow()
            }

            batch_or_transaction.set(balance_ref, update_data)
            
            logger.info(
                f"[{tenant_id}] Stock received | "
                f"product:{product_id} warehouse:{warehouse_id} "
                f"qty:{quantity} cost:{unit_cost} "
                f"new_avg_cost:{new_avg_cost:.2f}"
            )
            
            return update_data
        except Exception as e:
            logger.error(f"Error updating on receipt for tenant {tenant_id}, product {product_id}, warehouse {warehouse_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def reserve_stock(self, tenant_id: str, warehouse_id: str, product_id: str, quantity: float, batch_or_transaction: Any) -> Dict[str, Any]:
        try:
            db = get_db()
            balance_id = f"{tenant_id}_balance_{warehouse_id}_{product_id}"
            balance_ref = db.collection("tenants").document(tenant_id).collection("inventory_balances").document(balance_id)
            
            current_balance = await self.get_balance(tenant_id, warehouse_id, product_id, transaction=batch_or_transaction if isinstance(batch_or_transaction, AsyncTransaction) else None)

            current_on_hand = current_balance.get("on_hand_quantity", 0.0)
            current_reserved = current_balance.get("reserved_quantity", 0.0)
            
            available = current_on_hand - current_reserved

            if available < quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "INSUFFICIENT_STOCK",
                        "message": f"Insufficient stock. Available: {available}, Required: {quantity}"
                    }
                )
            
            updated_reserved = current_reserved + quantity
            
            update_data = {
                "id": balance_id,
                "tenant_id": tenant_id,
                "warehouse_id": warehouse_id,
                "product_id": product_id,
                "on_hand_quantity": current_on_hand,
                "reserved_quantity": updated_reserved,
                "average_cost": current_balance.get("average_cost", 0.0),
                "updated_at": datetime.utcnow()
            }
            
            batch_or_transaction.set(balance_ref, update_data)
            
            logger.info(
                f"[{tenant_id}] Stock reserved | "
                f"product:{product_id} qty:{quantity}"
            )

            return update_data
        except Exception as e:
            logger.error(f"Error reserving stock for tenant {tenant_id}, product {product_id}, warehouse {warehouse_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def release_stock(self, tenant_id: str, warehouse_id: str, product_id: str, quantity: float, batch_or_transaction: Any) -> Dict[str, Any]:
        try:
            db = get_db()
            balance_id = f"{tenant_id}_balance_{warehouse_id}_{product_id}"
            balance_ref = db.collection("tenants").document(tenant_id).collection("inventory_balances").document(balance_id)
            
            current_balance = await self.get_balance(tenant_id, warehouse_id, product_id, transaction=batch_or_transaction if isinstance(batch_or_transaction, AsyncTransaction) else None)

            current_on_hand = current_balance.get("on_hand_quantity", 0.0)
            current_reserved = current_balance.get("reserved_quantity", 0.0)
            
            updated_reserved = max(0.0, current_reserved - quantity)
            
            update_data = {
                "id": balance_id,
                "tenant_id": tenant_id,
                "warehouse_id": warehouse_id,
                "product_id": product_id,
                "on_hand_quantity": current_on_hand,
                "reserved_quantity": updated_reserved,
                "average_cost": current_balance.get("average_cost", 0.0),
                "updated_at": datetime.utcnow()
            }
            
            batch_or_transaction.set(balance_ref, update_data)
            
            logger.info(
                f"[{tenant_id}] Stock released | "
                f"product:{product_id} qty:{quantity}"
            )

            return update_data
        except Exception as e:
            logger.error(f"Error releasing stock for tenant {tenant_id}, product {product_id}, warehouse {warehouse_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def dispatch_stock(self, tenant_id: str, warehouse_id: str, product_id: str, quantity: float, batch_or_transaction: Any) -> Dict[str, Any]:
        try:
            db = get_db()
            balance_id = f"{tenant_id}_balance_{warehouse_id}_{product_id}"
            balance_ref = db.collection("tenants").document(tenant_id).collection("inventory_balances").document(balance_id)
            
            current_balance = await self.get_balance(tenant_id, warehouse_id, product_id, transaction=batch_or_transaction if isinstance(batch_or_transaction, AsyncTransaction) else None)

            current_on_hand = current_balance.get("on_hand_quantity", 0.0)
            current_reserved = current_balance.get("reserved_quantity", 0.0)
            
            if current_on_hand < quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "INSUFFICIENT_ON_HAND",
                        "message": "Cannot dispatch more than on-hand quantity"
                    }
                )
            
            updated_on_hand = max(0.0, current_on_hand - quantity)
            updated_reserved = max(0.0, current_reserved - quantity) 
            
            update_data = {
                "id": balance_id,
                "tenant_id": tenant_id,
                "warehouse_id": warehouse_id,
                "product_id": product_id,
                "on_hand_quantity": updated_on_hand,
                "reserved_quantity": updated_reserved,
                "average_cost": current_balance.get("average_cost", 0.0),
                "updated_at": datetime.utcnow()
            }
            
            batch_or_transaction.set(balance_ref, update_data)
            
            logger.info(
                f"[{tenant_id}] Stock dispatched | "
                f"product:{product_id} qty:{quantity}"
            )

            return update_data
        except Exception as e:
            logger.error(f"Error dispatching stock for tenant {tenant_id}, product {product_id}, warehouse {warehouse_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def issue_for_manufacturing(self, tenant_id: str, warehouse_id: str, product_id: str, quantity: float, batch_or_transaction: Any) -> Dict[str, Any]:
        try:
            db = get_db()
            balance_id = f"{tenant_id}_balance_{warehouse_id}_{product_id}"
            balance_ref = db.collection("tenants").document(tenant_id).collection("inventory_balances").document(balance_id)
            
            current_balance = await self.get_balance(tenant_id, warehouse_id, product_id, transaction=batch_or_transaction if isinstance(batch_or_transaction, AsyncTransaction) else None)

            current_on_hand = current_balance.get("on_hand_quantity", 0.0)
            current_reserved = current_balance.get("reserved_quantity", 0.0)
            
            available = current_on_hand - current_reserved

            if available < quantity:
                logger.warning(
                    f"[{tenant_id}] Manufacturing shortage | "
                    f"product:{product_id} "
                    f"required:{quantity} available:{available}"
                )
                return {
                    "success": False,
                    "available": available,
                    "required": quantity,
                    "shortage": quantity - available
                }
            
            updated_on_hand = current_on_hand - quantity
            
            update_data = {
                "id": balance_id,
                "tenant_id": tenant_id,
                "warehouse_id": warehouse_id,
                "product_id": product_id,
                "on_hand_quantity": updated_on_hand,
                "reserved_quantity": current_reserved,
                "average_cost": current_balance.get("average_cost", 0.0),
                "updated_at": datetime.utcnow()
            }
            
            batch_or_transaction.set(balance_ref, update_data)
            
            return {"success": True, "balance": update_data}
        except Exception as e:
            logger.error(f"Error issuing for manufacturing for tenant {tenant_id}, product {product_id}, warehouse {warehouse_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )