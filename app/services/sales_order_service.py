from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import HTTPException, status
from app.schemas.sales_order import SalesOrderCreateRequest, SalesOrderResponse, DispatchRequest, SalesOrderItemResponse
from app.schemas.error import ErrorDetail
from app.schemas.customer import CustomerResponse
from app.schemas.product import ProductResponse
from app.enums import OrderStatus, MovementType
from app.db.firebase import get_db
from firebase_admin import firestore
from firebase_admin.firestore import AsyncClient, AsyncDocumentReference, AsyncTransaction, AsyncWriteBatch, AsyncQuery
from app.core.logger import get_logger
from app.core.audit import AuditService, AuditEvents
# from app.services.customer_service import CustomerService # Removed from module level
# from app.services.product_service import ProductService # Removed from module level
# from app.services.inventory_service import InventoryService # Removed from module level
# from app.services.ledger_service import LedgerService # Removed from module level
# from app.services.warehouse_service import WarehouseService # Removed from module level
from uuid import uuid4

logger = get_logger(__name__)

class SalesOrderService:
    async def get(self, tenant_id: str, order_id: str) -> SalesOrderResponse:
        try:
            db = get_db()
            order_ref = db.collection("tenants").document(tenant_id).collection("sales_orders").document(order_id)
            doc = await order_ref.get()
            
            if not doc.exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "ORDER_NOT_FOUND",
                        "message": f"Sales Order {order_id} not found"
                    }
                )
            
            return SalesOrderResponse(**doc.to_dict())
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting sales order {order_id} for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def list(self, tenant_id: str, status_filter: Optional[OrderStatus] = None) -> List[SalesOrderResponse]:
        try:
            db = get_db()
            query: AsyncQuery = db.collection("tenants").document(tenant_id).collection("sales_orders")
            
            if status_filter:
                query = query.where("status", "==", status_filter.value)
            
            query = query.order_by("created_at", direction=firestore.Query.DESCENDING)
            
            docs = await query.get()
            
            return [SalesOrderResponse(**doc.to_dict()) for doc in docs]
        except Exception as e:
            logger.error(f"Error listing sales orders for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def create(self, tenant_id: str, data: SalesOrderCreateRequest) -> SalesOrderResponse:
        from app.services.customer_service import CustomerService # Import locally
        from app.services.product_service import ProductService # Import locally
        from app.services.warehouse_service import WarehouseService # Import locally
        
        customer_service = CustomerService()
        product_service = ProductService()
        warehouse_service = WarehouseService()

        try:
            db = get_db()
            errors: List[ErrorDetail] = []
            
            # Step 1: Validate customer exists
            customer: CustomerResponse = await customer_service.get(tenant_id, data.customer_id)
            # get() raises 404 if not found, so no need for explicit check here
            
            # Validate warehouse active
            await warehouse_service.validate_active(tenant_id, data.warehouse_id)

            # Step 2: Check order number uniqueness
            order_id = f"{tenant_id}_order_{data.order_number.lower()}"
            order_ref = db.collection("tenants").document(tenant_id).collection("sales_orders").document(order_id)
            doc = await order_ref.get()
            if doc.exists:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "ORDER_NUMBER_EXISTS",
                        "message": f"Order number {data.order_number} already exists"
                    }
                )
            
            # Step 3: Validate all items and build order items
            order_items_data: List[Dict[str, Any]] = []
            subtotal = 0.0
            
            for item_request in data.items:
                try:
                    product: ProductResponse = await product_service.get_by_sku(tenant_id, item_request.sku)
                    
                    # b. Check product active
                    if not product.active:
                        errors.append(ErrorDetail(
                            field=f"items.{item_request.sku}",
                            message=f"Product {item_request.sku} is inactive and cannot be sold"
                        ))
                    
                    # c. Check product sellable
                    if not product.sellable:
                        errors.append(ErrorDetail(
                            field=f"items.{item_request.sku}",
                            message=f"Product {item_request.sku} is not marked as sellable"
                        ))
                    
                    if not errors: # Only build item if no errors for this product
                        line_total = item_request.quantity * product.selling_price
                        order_items_data.append({
                            "product_id": product.id,
                            "sku": product.sku,
                            "product_name": product.name,
                            "quantity": item_request.quantity,
                            "unit_price": product.selling_price,
                            "dispatched_quantity": 0.0,
                            "line_total": line_total
                        })
                        subtotal += line_total
                except HTTPException as e:
                    if e.status_code == status.HTTP_404_NOT_FOUND:
                        errors.append(ErrorDetail(
                            field=f"items.{item_request.sku}",
                            message=f"Product {item_request.sku} not found"
                        ))
                    else:
                        raise # Re-raise other HTTP exceptions
            
            if errors:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "SALES_ORDER_VALIDATION_FAILED",
                        "message": "One or more items failed validation",
                        "details": [e.model_dump() for e in errors]
                    }
                )
            
            # Step 4: Calculate totals server-side
            tax = round(subtotal * data.tax_percent / 100, 2)
            grand_total = round(subtotal + tax, 2)

            # Step 5: Write sales order document
            sales_order_data = {
                "id": order_id,
                "tenant_id": tenant_id,
                "customer_id": data.customer_id,
                "customer_name": customer.name,
                "order_number": data.order_number,
                "warehouse_id": data.warehouse_id, # Store warehouse_id on the order
                "status": OrderStatus.draft.value,
                "items": order_items_data,
                "tax_percent": data.tax_percent,
                "subtotal": subtotal,
                "tax": tax,
                "grand_total": grand_total,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "created_by": "system"
            }
            await order_ref.set(sales_order_data)
            
            # Log
            logger.info(
                f"[{tenant_id}] Sales order created | "
                f"order:{data.order_number} "
                f"total:{grand_total}"
            )

            # 6. Return SalesOrderResponse
            return SalesOrderResponse(**sales_order_data)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating sales order for tenant {tenant_id}, order number {data.order_number}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def confirm(self, tenant_id: str, order_id: str) -> SalesOrderResponse:
        from app.services.inventory_service import InventoryService # Import locally
        from app.services.ledger_service import LedgerService # Import locally
        
        inventory_service = InventoryService()
        ledger_service = LedgerService()

        try:
            db = get_db()
            
            # Step 1: Fetch sales order
            order_doc = await self.get(tenant_id, order_id) # This will raise 404 if not found
            order_data = order_doc.model_dump()

            if order_data["status"] != OrderStatus.draft.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "INVALID_ORDER_STATUS",
                        "message": f"Only draft orders can be confirmed. Current status: {order_data['status']}"
                    }
                )
            
            # Step 2: Check stock availability for ALL items first
            shortages: List[Dict[str, Any]] = []
            reservations_to_make: List[Dict[str, Any]] = []
            
            for item in order_data["items"]:
                balance = await inventory_service.get_balance(
                    tenant_id, order_data["warehouse_id"], item["product_id"]
                )
                
                available = balance["on_hand_quantity"] - balance["reserved_quantity"]
                
                if available < item["quantity"]:
                    shortages.append({
                        "sku": item["sku"],
                        "required": item["quantity"],
                        "available": available,
                        "shortage": item["quantity"] - available
                    })
                else:
                    reservations_to_make.append({
                        "product_id": item["product_id"],
                        "sku": item["sku"],
                        "quantity": item["quantity"],
                        "average_cost": balance["average_cost"] # Store average cost for ledger
                    })
            
            if shortages:
                logger.warning(
                    f"[{tenant_id}] Order confirmation failed | "
                    f"order:{order_id} insufficient stock"
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "INSUFFICIENT_STOCK_FOR_CONFIRMATION",
                        "message": "Insufficient stock to confirm order",
                        "details": shortages
                    }
                )
            
            # Step 3: All available — use Firestore transaction for reservations
            order_ref = db.collection("tenants").document(tenant_id).collection("sales_orders").document(order_id)

            @firestore.async_transactional
            async def reserve_in_transaction(transaction: AsyncTransaction):
                # Re-fetch order inside transaction to ensure latest status
                order_snapshot = await order_ref.get(transaction=transaction)
                current_order_data = order_snapshot.to_dict()
                if current_order_data["status"] != OrderStatus.draft.value:
                    logger.warning(
                        f"[{tenant_id}] Concurrent reservation conflict | "
                        f"order:{order_id}"
                    )
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "error": "INVALID_ORDER_STATUS",
                            "message": f"Order status changed during confirmation. Current status: {current_order_data['status']}"
                        }
                    )

                for reservation in reservations_to_make:
                    await inventory_service.reserve_stock(
                        tenant_id=tenant_id,
                        warehouse_id=order_data["warehouse_id"],
                        product_id=reservation["product_id"],
                        quantity=reservation["quantity"],
                        batch_or_transaction=transaction # Pass transaction
                    )
            
            await reserve_in_transaction(db.transaction()) # Run the transaction
            
            # Step 4: After transaction succeeds write ledger entries and update order status
            batch = db.batch()
            ledger_entry_ids = []
            
            for reservation in reservations_to_make:
                entry_dict = await ledger_service.build_entry(
                    tenant_id=tenant_id,
                    warehouse_id=order_data["warehouse_id"],
                    product_id=reservation["product_id"],
                    movement_type=MovementType.sales_reservation,
                    quantity_change=reservation["quantity"], # Positive change for reserved quantity
                    unit_cost=reservation["average_cost"],
                    reference_type="sales_order",
                    reference_id=order_id
                )
                ledger_id = await ledger_service.append_to_batch(batch, tenant_id, entry_dict)
                ledger_entry_ids.append(ledger_id)
            
            batch.update(order_ref, {
                "status": OrderStatus.confirmed.value,
                "updated_at": datetime.utcnow(),
                "ledger_entry_ids": firestore.ArrayUnion(ledger_entry_ids) # Add new ledger IDs
            })
            
            await batch.commit()
            
            # Log and Audit
            logger.info(
                f"[{tenant_id}] Order confirmed | "
                f"order:{order_id}"
            )
            audit_service = AuditService()
            await audit_service.log(
                tenant_id=tenant_id,
                event_type=AuditEvents.SALES_ORDER_CONFIRMED,
                entity_type="sales_order",
                entity_id=order_id,
                description=f"Sales order confirmed: {order_data['order_number']}",
                metadata={"items_count": len(order_data["items"])}
            )

            # Step 5: Fetch and return updated SalesOrderResponse
            updated_order_doc = await self.get(tenant_id, order_id)
            return updated_order_doc
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error confirming sales order {order_id} for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def dispatch(self, tenant_id: str, order_id: str, data: DispatchRequest) -> SalesOrderResponse:
        from app.services.inventory_service import InventoryService # Import locally
        from app.services.ledger_service import LedgerService # Import locally
        
        inventory_service = InventoryService()
        ledger_service = LedgerService()

        try:
            db = get_db()
            
            # Step 1: Fetch order
            order_doc = await self.get(tenant_id, order_id) # This will raise 404 if not found
            order_data = order_doc.model_dump()

            if order_data["status"] not in [OrderStatus.confirmed.value, OrderStatus.partially_dispatched.value]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "INVALID_ORDER_STATUS",
                        "message": "Only confirmed or partially dispatched orders can be dispatched"
                    }
                )
            
            # Step 2: Validate dispatch items
            errors: List[ErrorDetail] = []
            dispatch_data_processed: List[Dict[str, Any]] = []
            
            # Create a mutable copy of order items to track dispatched quantities
            current_order_items = [SalesOrderItemResponse(**item) for item in order_data["items"]]
            
            for dispatch_item_request in data.items:
                matching_order_item: Optional[SalesOrderItemResponse] = None
                for item in current_order_items:
                    if item.sku == dispatch_item_request.sku:
                        matching_order_item = item
                        break
                
                if not matching_order_item:
                    errors.append(ErrorDetail(
                        field=f"items.{dispatch_item_request.sku}",
                        message=f"SKU {dispatch_item_request.sku} not found in order"
                    ))
                    continue
                
                remaining_to_dispatch = matching_order_item.quantity - matching_order_item.dispatched_quantity
                
                if dispatch_item_request.quantity > remaining_to_dispatch:
                    errors.append(ErrorDetail(
                        field=f"items.{dispatch_item_request.sku}",
                        message=f"Cannot dispatch {dispatch_item_request.quantity} units of {dispatch_item_request.sku}. Remaining to dispatch: {remaining_to_dispatch}"
                    ))
                    continue
                
                # Update dispatched quantity for this item in our mutable list
                matching_order_item.dispatched_quantity += dispatch_item_request.quantity
                
                dispatch_data_processed.append({
                    "product_id": matching_order_item.product_id,
                    "sku": matching_order_item.sku,
                    "quantity": dispatch_item_request.quantity,
                    "unit_price": matching_order_item.unit_price # Use selling price as unit cost for dispatch ledger
                })
            
            if errors:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "DISPATCH_VALIDATION_FAILED",
                        "message": "One or more dispatch items failed validation",
                        "details": [e.model_dump() for e in errors]
                    }
                )
            
            # Step 3: Build batch
            batch = db.batch()
            ledger_entry_ids = []
            
            for dispatch_item in dispatch_data_processed:
                # a. Update balance (on_hand and reserved)
                await inventory_service.dispatch_stock(
                    tenant_id=tenant_id,
                    warehouse_id=order_data["warehouse_id"],
                    product_id=dispatch_item["product_id"],
                    quantity=dispatch_item["quantity"],
                    batch_or_transaction=batch
                )
                
                # b. Add ledger entry
                entry_dict = await ledger_service.build_entry(
                    tenant_id=tenant_id,
                    warehouse_id=order_data["warehouse_id"],
                    product_id=dispatch_item["product_id"],
                    movement_type=MovementType.sales_dispatch,
                    quantity_change=-dispatch_item["quantity"], # Negative change for stock out
                    unit_cost=dispatch_item["unit_price"],
                    reference_type="sales_order",
                    reference_id=order_id
                )
                ledger_id = await ledger_service.append_to_batch(batch, tenant_id, entry_dict)
                ledger_entry_ids.append(ledger_id)
            
            # c. Update order items dispatched quantities and determine new status
            all_dispatched = all(item.dispatched_quantity >= item.quantity for item in current_order_items)
            new_status = OrderStatus.dispatched.value if all_dispatched else OrderStatus.partially_dispatched.value
            
            order_ref = db.collection("tenants").document(tenant_id).collection("sales_orders").document(order_id)
            batch.update(order_ref, {
                "items": [item.model_dump() for item in current_order_items],
                "status": new_status,
                "updated_at": datetime.utcnow(),
                "ledger_entry_ids": firestore.ArrayUnion(ledger_entry_ids) # Add new ledger IDs
            })
            
            await batch.commit()
            
            # Log and Audit
            logger.info(
                f"[{tenant_id}] Order dispatched | "
                f"order:{order_id} status:{new_status}"
            )
            audit_service = AuditService()
            await audit_service.log(
                tenant_id=tenant_id,
                event_type=AuditEvents.STOCK_DISPATCHED,
                entity_type="sales_order",
                entity_id=order_id,
                description=f"Stock dispatched for order: {order_id}",
                metadata={
                    "status": new_status,
                    "dispatched_items": len(data.items)
                }
            )

            # Step 4: Return updated SalesOrderResponse
            updated_order_doc = await self.get(tenant_id, order_id)
            return updated_order_doc
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error dispatching sales order {order_id} for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def cancel(self, tenant_id: str, order_id: str) -> SalesOrderResponse:
        from app.services.inventory_service import InventoryService # Import locally
        from app.services.ledger_service import LedgerService # Import locally
        
        inventory_service = InventoryService()
        ledger_service = LedgerService()

        try:
            db = get_db()
            
            # Step 1: Fetch order
            order_doc = await self.get(tenant_id, order_id) # This will raise 404 if not found
            order_data = order_doc.model_dump()

            if order_data["status"] == OrderStatus.dispatched.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "CANNOT_CANCEL_DISPATCHED",
                        "message": "Fully dispatched orders cannot be cancelled"
                    }
                )
            if order_data["status"] == OrderStatus.cancelled.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "ALREADY_CANCELLED",
                        "message": "Order is already cancelled"
                    }
                )
            
            # Step 2: Build batch
            batch = db.batch()
            ledger_entry_ids = []
            
            # Only release stock if order was confirmed (draft orders have no reservations to release)
            if order_data["status"] in [OrderStatus.confirmed.value, OrderStatus.partially_dispatched.value]:
                for item in order_data["items"]:
                    unreleased_qty = item["quantity"] - item["dispatched_quantity"]
                    
                    if unreleased_qty > 0:
                        # Release stock (reduces reserved_quantity)
                        await inventory_service.release_stock(
                            tenant_id=tenant_id,
                            warehouse_id=order_data["warehouse_id"],
                            product_id=item["product_id"],
                            quantity=unreleased_qty,
                            batch_or_transaction=batch
                        )
                        
                        # Build ledger entry for reservation release
                        balance = await inventory_service.get_balance(tenant_id, order_data["warehouse_id"], item["product_id"])
                        entry_dict = await ledger_service.build_entry(
                            tenant_id=tenant_id,
                            warehouse_id=order_data["warehouse_id"],
                            product_id=item["product_id"],
                            movement_type=MovementType.reservation_release,
                            quantity_change=-unreleased_qty, # Negative change for reserved quantity
                            unit_cost=balance.get("average_cost", 0.0), # Use current average cost for ledger
                            reference_type="sales_order",
                            reference_id=order_id
                        )
                        ledger_id = await ledger_service.append_to_batch(batch, tenant_id, entry_dict)
                        ledger_entry_ids.append(ledger_id)
            
            order_ref = db.collection("tenants").document(tenant_id).collection("sales_orders").document(order_id)
            batch.update(order_ref, {
                "status": OrderStatus.cancelled.value,
                "updated_at": datetime.utcnow(),
                "ledger_entry_ids": firestore.ArrayUnion(ledger_entry_ids) # Add new ledger IDs
            })
            
            await batch.commit()
            
            # Log and Audit
            logger.info(
                f"[{tenant_id}] Order cancelled | "
                f"order:{order_id}"
            )
            audit_service = AuditService()
            await audit_service.log(
                tenant_id=tenant_id,
                event_type=AuditEvents.ORDER_CANCELLED,
                entity_type="sales_order",
                entity_id=order_id,
                description=f"Order cancelled: {order_id}",
                metadata={"previous_status": order_data["status"]}
            )

            # Step 3: Return updated SalesOrderResponse
            updated_order_doc = await self.get(tenant_id, order_id)
            return updated_order_doc
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error cancelling sales order {order_id} for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )