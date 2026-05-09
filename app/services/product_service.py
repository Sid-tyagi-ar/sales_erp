from typing import List, Optional
from app.schemas.product import ProductCreateRequest, ProductUpdateRequest, ProductResponse

class ProductService:
    async def create(self, tenant_id: str, data: ProductCreateRequest) -> ProductResponse:
        """
        TODO: check SKU uniqueness, write to tenants/{tenant_id}/products/{id}
        """
        # Placeholder for now
        product_id = f"{tenant_id}_product_{data.sku.lower()}"
        return ProductResponse(
            id=product_id,
            sku=data.sku,
            name=data.name,
            type=data.type,
            unit_of_measure=data.unit_of_measure,
            standard_cost=data.standard_cost,
            selling_price=data.selling_price,
            active=True,
            sellable=data.sellable
        )

    async def get(self, tenant_id: str, product_id: str) -> Optional[ProductResponse]:
        """
        TODO: Implement DB logic to retrieve a product by ID.
        """
        return None

    async def list(self, tenant_id: str) -> List[ProductResponse]:
        """
        TODO: Implement DB logic to list all products for a tenant.
        """
        return []

    async def update(self, tenant_id: str, product_id: str, data: ProductUpdateRequest) -> Optional[ProductResponse]:
        """
        TODO: Implement DB logic to update a product.
        """
        return None
