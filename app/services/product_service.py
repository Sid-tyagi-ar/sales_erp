from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import HTTPException, status
from app.schemas.product import ProductCreateRequest, ProductUpdateRequest, ProductResponse
from app.enums import ProductType
from app.db.firebase import get_db
from firebase_admin import firestore
from app.core.logger import get_logger
from app.core.audit import AuditService, AuditEvents

logger = get_logger(__name__)

class ProductService:
    async def create(self, tenant_id: str, data: ProductCreateRequest) -> ProductResponse:
        try:
            db = get_db()
            
            # 1. Generate deterministic id
            product_id = f"{tenant_id}_product_{data.sku.lower()}"
            product_ref = db.collection("tenants").document(tenant_id).collection("products").document(product_id)
            
            # 2. Check document exists
            doc = await product_ref.get()
            if doc.exists:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "PRODUCT_ALREADY_EXISTS",
                        "message": f"SKU {data.sku} already exists for this tenant"
                    }
                )
            
            # 3. If type is finished_good force sellable=True
            if data.type == ProductType.finished_good:
                data.sellable = True

            # 4. Build and write document
            product_data = {
                "id": product_id,
                "tenant_id": tenant_id,
                "name": data.name,
                "sku": data.sku.upper(), # Ensure SKU is uppercase in DB
                "type": data.type.value,
                "unit_of_measure": data.unit_of_measure,
                "standard_cost": data.standard_cost,
                "selling_price": data.selling_price,
                "active": True,
                "sellable": data.sellable,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "created_by": "system"
            }
            await product_ref.set(product_data)
            
            # Log and Audit
            logger.info(f"[{tenant_id}] Product created: {data.sku}")
            audit_service = AuditService()
            await audit_service.log(
                tenant_id=tenant_id,
                event_type=AuditEvents.PRODUCT_CREATED,
                entity_type="product",
                entity_id=product_id,
                description=f"Product created: {data.sku}",
                metadata={"type": data.type.value, "sku": data.sku}
            )

            # 5. Return ProductResponse
            return ProductResponse(**product_data)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating product {data.sku} for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def get(self, tenant_id: str, product_id: str) -> ProductResponse:
        try:
            db = get_db()
            product_ref = db.collection("tenants").document(tenant_id).collection("products").document(product_id)
            doc = await product_ref.get()
            
            if not doc.exists:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "PRODUCT_NOT_FOUND",
                        "message": f"Product {product_id} not found"
                    }
                )
            
            return ProductResponse(**doc.to_dict())
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching product {product_id} for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def get_by_sku(self, tenant_id: str, sku: str) -> ProductResponse:
        try:
            logger.debug(f"[{tenant_id}] Fetching product by SKU: {sku}")
            # 1. Construct deterministic id from sku
            product_id = f"{tenant_id}_product_{sku.lower()}"
            # 2. Reuse get() with constructed id
            return await self.get(tenant_id, product_id)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error fetching product by SKU {sku} for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def list(self, tenant_id: str) -> List[ProductResponse]:
        try:
            db = get_db()
            products_ref = db.collection("tenants").document(tenant_id).collection("products")
            docs = await products_ref.get()
            
            return [ProductResponse(**doc.to_dict()) for doc in docs]
        except Exception as e:
            logger.error(f"Error listing products for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def update(self, tenant_id: str, product_id: str, data: ProductUpdateRequest) -> ProductResponse:
        try:
            db = get_db()
            
            # 1. Confirm exists via get()
            # This will raise HTTPException if not found
            existing_product = await self.get(tenant_id, product_id) 
            
            product_ref = db.collection("tenants").document(tenant_id).collection("products").document(product_id)
            
            # 2. Build dict of only non-None fields
            update_data = data.model_dump(exclude_unset=True)
            
            # always add updated_at: datetime.utcnow()
            update_data["updated_at"] = datetime.utcnow()
            
            if not update_data:
                pass

            await product_ref.update(update_data)
            
            # Log and Audit
            logger.info(f"[{tenant_id}] Product updated: {product_id}")
            audit_service = AuditService()
            await audit_service.log(
                tenant_id=tenant_id,
                event_type=AuditEvents.PRODUCT_UPDATED,
                entity_type="product",
                entity_id=product_id,
                description=f"Product {existing_product.sku} updated",
                metadata={"updates": update_data}
            )

            # 4. Fetch and return updated ProductResponse
            updated_doc = await product_ref.get()
            return ProductResponse(**updated_doc.to_dict())
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating product {product_id} for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def validate_active_sellable(self, tenant_id: str, sku: str) -> ProductResponse:
        try:
            # 1. Call get_by_sku()
            product = await self.get_by_sku(tenant_id, sku)
            
            # 2. If product.active is False raise HTTPException 400
            if not product.active:
                logger.warning(f"[{tenant_id}] Inactive product access attempted: {sku}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "PRODUCT_INACTIVE",
                        "message": f"Product {sku} is inactive and cannot be used"
                    }
                )
            
            # 3. If product.sellable is False raise HTTPException 400
            if not product.sellable:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "PRODUCT_NOT_SELLABLE",
                        "message": f"Product {sku} is not marked as sellable"
                    }
                )
            
            # 4. Return product
            return product
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error validating active/sellable product {sku} for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def validate_active(self, tenant_id: str, sku: str) -> ProductResponse:
        try:
            # 1. Call get_by_sku()
            product = await self.get_by_sku(tenant_id, sku)
            
            # 2. If product.active is False raise HTTPException 400
            if not product.active:
                logger.warning(f"[{tenant_id}] Inactive product access attempted: {sku}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "PRODUCT_INACTIVE",
                        "message": f"Product {sku} is inactive and cannot be used"
                    }
                )
            
            # 3. Return product
            return product
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error validating active product {sku} for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )
