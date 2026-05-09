from typing import List, Dict, Any, Set, Optional
from datetime import datetime
from fastapi import HTTPException, status
from app.schemas.bom import BOMCreateRequest, BOMResponse, BOMEntryResponse
from app.schemas.error import ErrorDetail
from app.enums import ProductType
from app.db.firebase import get_db
from firebase_admin import firestore
from app.core.logger import get_logger
from app.core.audit import AuditService, AuditEvents

logger = get_logger(__name__)

class BOMService:
    async def get_bom_for_product(self, tenant_id: str, finished_good_id: str) -> List[Dict[str, Any]]:
        try:
            db = get_db()
            bom_ref = db.collection("tenants").document(tenant_id).collection("bom")
            query = bom_ref.where("finished_good_id", "==", finished_good_id)
            docs = await query.get()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            logger.error(f"Error getting BOM for product {finished_good_id} for tenant {tenant_id}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def _traverse_circular(self, tenant_id: str, product_id: str, visited: Set[str]) -> bool:
        if product_id in visited:
            return True
        visited.add(product_id)
        
        bom_entries = await self.get_bom_for_product(tenant_id, product_id)
        for entry in bom_entries:
            if await self._traverse_circular(tenant_id, entry["raw_material_id"], visited):
                return True
        return False

    async def check_circular(self, tenant_id: str, finished_good_id: str, new_component_id: str) -> bool:
        # Note: pre-seed visited with finished_good_id so if component's BOM ever references it, cycle detected
        is_circular = await self._traverse_circular(tenant_id, new_component_id, {finished_good_id})
        if is_circular:
            logger.warning(
                f"[{tenant_id}] Circular BOM detected | "
                f"finished_good:{finished_good_id} "
                f"component:{new_component_id}"
            )
        return is_circular

    async def create(self, tenant_id: str, data: BOMCreateRequest) -> BOMResponse:
        from app.services.product_service import ProductService # Import locally
        product_service = ProductService() # Instantiate locally

        try:
            db = get_db()
            errors: List[ErrorDetail] = []
            
            # Step 1: Validate finished good
            try:
                finished_good_product = await product_service.get_by_sku(tenant_id, data.finished_good_sku)
                if finished_good_product.type != ProductType.finished_good:
                    errors.append(ErrorDetail(
                        field="finished_good_sku",
                        message="BOM can only be defined for finished goods"
                    ))
            except HTTPException as e:
                if e.status_code == status.HTTP_404_NOT_FOUND:
                    errors.append(ErrorDetail(
                        field="finished_good_sku",
                        message=f"Finished good SKU {data.finished_good_sku} not found"
                    ))
                else:
                    raise # Re-raise other HTTP exceptions
            
            if errors:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "BOM_VALIDATION_FAILED",
                        "message": "One or more components failed validation",
                        "details": [e.model_dump() for e in errors]
                    }
                )

            finished_good_id = finished_good_product.id
            
            # Step 2: For each component in data.components
            component_products: Dict[str, Any] = {} # Store fetched product data to avoid re-fetching
            for component_request in data.components:
                try:
                    component_product = await product_service.get_by_sku(tenant_id, component_request.raw_material_sku)
                    component_products[component_request.raw_material_sku] = component_product

                    # b. If found but inactive add to errors
                    if not component_product.active:
                        errors.append(ErrorDetail(
                            field=f"components.{component_request.raw_material_sku}",
                            message=f"Component {component_request.raw_material_sku} is inactive"
                        ))
                    
                    # c. If component sku == finished_good sku add to errors
                    if component_request.raw_material_sku == data.finished_good_sku:
                        errors.append(ErrorDetail(
                            field=f"components.{component_request.raw_material_sku}",
                            message="Product cannot be its own component"
                        ))
                    
                    # d. Run check_circular
                    if await self.check_circular(tenant_id, finished_good_id, component_product.id):
                        errors.append(ErrorDetail(
                            field=f"components.{component_request.raw_material_sku}",
                            message=f"Adding {component_request.raw_material_sku} creates a circular reference. {component_request.raw_material_sku} directly or indirectly requires {data.finished_good_sku} to be manufactured"
                        ))

                except HTTPException as e:
                    if e.status_code == status.HTTP_404_NOT_FOUND:
                        errors.append(ErrorDetail(
                            field=f"components.{component_request.raw_material_sku}",
                            message=f"Component SKU {component_request.raw_material_sku} not found"
                        ))
                    else:
                        raise # Re-raise other HTTP exceptions
            
            # Step 3: If any errors collected raise HTTPException 400
            if errors:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "BOM_VALIDATION_FAILED",
                        "message": "One or more components failed validation",
                        "details": [e.model_dump() for e in errors]
                    }
                )
            
            # Step 4: All valid — write all entries in one batch
            batch = db.batch()
            bom_entries_for_response: List[BOMEntryResponse] = []

            for component_request in data.components:
                component_product = component_products[component_request.raw_material_sku]
                
                bom_id = f"{tenant_id}_bom_{finished_good_id}_{component_product.id}"
                
                effective_quantity = component_request.quantity_required * (1 + component_request.wastage_percent / 100)

                entry_data = {
                    "id": bom_id,
                    "tenant_id": tenant_id,
                    "finished_good_id": finished_good_id,
                    "raw_material_id": component_product.id,
                    "raw_material_sku": component_product.sku,
                    "quantity_required": component_request.quantity_required,
                    "wastage_percent": component_request.wastage_percent,
                    "effective_quantity": effective_quantity,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                bom_ref = db.collection("tenants").document(tenant_id).collection("bom").document(bom_id)
                batch.set(bom_ref, entry_data)

                bom_entries_for_response.append(BOMEntryResponse(
                    raw_material_sku=component_product.sku,
                    raw_material_name=component_product.name,
                    quantity_required=component_request.quantity_required,
                    wastage_percent=component_request.wastage_percent,
                    effective_quantity=effective_quantity
                ))
            
            await batch.commit()
            
            # Log and Audit
            logger.info(
                f"[{tenant_id}] BOM created for: {finished_good_product.sku} "
                f"with {len(data.components)} components"
            )
            audit_service = AuditService()
            await audit_service.log(
                tenant_id=tenant_id,
                event_type=AuditEvents.BOM_CREATED,
                entity_type="bom",
                entity_id=finished_good_id,
                description=f"BOM created for {finished_good_product.sku}",
                metadata={
                    "finished_good_sku": finished_good_product.sku,
                    "component_count": len(data.components)
                }
            )

            # Step 5: Return BOMResponse
            return BOMResponse(
                finished_good_sku=finished_good_product.sku,
                finished_good_name=finished_good_product.name,
                components=bom_entries_for_response
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error creating BOM for tenant {tenant_id}, finished good {data.finished_good_sku}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )

    async def get(self, tenant_id: str, finished_good_sku: str) -> BOMResponse:
        from app.services.product_service import ProductService # Import locally
        product_service = ProductService() # Instantiate locally

        try:
            db = get_db()
            
            # 1. Fetch product by sku to get finished_good_id
            finished_good_product = await product_service.get_by_sku(tenant_id, finished_good_sku)
            finished_good_id = finished_good_product.id

            # 2. Call get_bom_for_product()
            bom_entries_data = await self.get_bom_for_product(tenant_id, finished_good_id)
            
            # 3. If empty list raise 404
            if not bom_entries_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "BOM_NOT_FOUND",
                        "message": f"No BOM defined for {finished_good_sku}"
                    }
                )
            
            # Build BOMEntryResponse list
            bom_entries_for_response: List[BOMEntryResponse] = []
            for entry_data in bom_entries_data:
                # Fetch component product name for response
                component_product = await product_service.get(tenant_id, entry_data["raw_material_id"])
                
                bom_entries_for_response.append(BOMEntryResponse(
                    raw_material_sku=entry_data["raw_material_sku"],
                    raw_material_name=component_product.name,
                    quantity_required=entry_data["quantity_required"],
                    wastage_percent=entry_data["wastage_percent"],
                    effective_quantity=entry_data["effective_quantity"]
                ))
            
            return BOMResponse(
                finished_good_sku=finished_good_product.sku,
                finished_good_name=finished_good_product.name,
                components=bom_entries_for_response
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting BOM for tenant {tenant_id}, finished good {finished_good_sku}: {e}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={"error": "INTERNAL_ERROR", "message": f"An unexpected error occurred: {e}"}
            )