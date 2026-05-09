from typing import List, Optional
from datetime import datetime
from app.schemas.sales_order import SalesOrderCreateRequest, SalesOrderResponse, DispatchRequest

class SalesOrderService:
    async def create(self, tenant_id: str, data: SalesOrderCreateRequest) -> SalesOrderResponse:
        """
        TODO: Implement DB logic to create a sales order.
        """
        # Placeholder for now
        return SalesOrderResponse(
            id="so_placeholder_id",
            order_number=data.order_number,
            customer_id=data.customer_id,
            customer_name="Placeholder Customer", # This would come from customer service
            status="draft",
            items=[], # This would be populated from data
            subtotal=0.0,
            tax=0.0,
            grand_total=0.0,
            created_at=datetime.utcnow()
        )

    async def confirm(self, tenant_id: str, order_id: str) -> Optional[SalesOrderResponse]:
        """
        TODO: Firestore transaction for reservation
        """
        return None

    async def dispatch(self, tenant_id: str, order_id: str, data: DispatchRequest) -> Optional[SalesOrderResponse]:
        """
        TODO: batch write dispatch + ledger + status update
        """
        return None

    async def cancel(self, tenant_id: str, order_id: str) -> Optional[SalesOrderResponse]:
        """
        TODO: release reservation batch
        """
        return None
