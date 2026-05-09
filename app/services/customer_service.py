from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import HTTPException, status
from app.schemas.customer import CustomerCreateRequest, CustomerResponse
from app.db.firebase import get_db
from firebase_admin import firestore
from app.core.logger import get_logger

logger = get_logger(__name__)

class CustomerService:
    async def create(self, tenant_id: str, data: CustomerCreateRequest) -> CustomerResponse:
        try:
            db = get_db()
            
            # 1. Generate deterministic id from email
            customer_id = f"{tenant_id}_customer_{data.email.lower().replace('@','_').replace('.','_')}"
            customer_ref = db.collection("tenants").document(tenant_id).collection("customers").document(customer_id)
            
            # 2. Check document exists
            doc = await customer_ref.get()
            if doc.exists:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "CUSTOMER_ALREADY_EXISTS",
                        "message": f"Customer with email {data.email} already exists"
                    }
                )
            
            # 3. Build and write document
            customer_data = {
                "id": customer_id,
                "tenant_id": tenant_id,
                "name": data.name,
                "email": data.email,
                "phone": data.phone,
                "address": data.address,
                "active": True, # Assuming customers are active by default
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "created_by": "system"
            }
            await customer_ref.set(customer_data)
            
            logger.info(f"[{tenant_id}] Customer created: {data.email}")
            # No specific audit event for customer creation was requested.

            # 4. Return CustomerResponse
            return CustomerResponse(**customer_data)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating customer {data.email} for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def get(self, tenant_id: str, customer_id: str) -> CustomerResponse:
        try:
            db = get_db()
            customer_ref = db.collection("tenants").document(tenant_id).collection("customers").document(customer_id)
            doc = await customer_ref.get()
            
            if not doc.exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "CUSTOMER_NOT_FOUND",
                        "message": f"Customer {customer_id} not found"
                    }
                )
            
            return CustomerResponse(**doc.to_dict())
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching customer {customer_id} for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def list(self, tenant_id: str) -> List[CustomerResponse]:
        try:
            db = get_db()
            customers_ref = db.collection("tenants").document(tenant_id).collection("customers")
            docs = await customers_ref.get()
            
            return [CustomerResponse(**doc.to_dict()) for doc in docs]
        except Exception as e:
            logger.error(f"Error listing customers for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )
