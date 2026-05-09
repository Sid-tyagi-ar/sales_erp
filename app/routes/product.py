from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List
from app.schemas.product import ProductCreateRequest, ProductUpdateRequest, ProductResponse
from app.schemas.error import ErrorResponse
from app.services.product_service import ProductService

router = APIRouter(prefix="/products", tags=["Products"])

@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def create_product(
    request: Request,
    product_data: ProductCreateRequest,
    product_service: ProductService = Depends()
):
    try:
        tenant_id = request.state.tenant_id
        product = await product_service.create(tenant_id, product_data)
        return product
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorResponse(error="ValueError", message=str(e)).model_dump())
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorResponse(error="ServerError", message=str(e)).model_dump())

@router.get(
    "/",
    response_model=List[ProductResponse],
    responses={500: {"model": ErrorResponse}}
)
async def list_products(
    request: Request,
    product_service: ProductService = Depends()
):
    try:
        tenant_id = request.state.tenant_id
        products = await product_service.list(tenant_id)
        return products
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorResponse(error="ServerError", message=str(e)).model_dump())

@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def get_product(
    request: Request,
    product_id: str,
    product_service: ProductService = Depends()
):
    tenant_id = request.state.tenant_id
    product = await product_service.get(tenant_id, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorResponse(error="NotFound", message="Product not found").model_dump())
    return product

@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def update_product(
    request: Request,
    product_id: str,
    product_data: ProductUpdateRequest,
    product_service: ProductService = Depends()
):
    tenant_id = request.state.tenant_id
    product = await product_service.update(tenant_id, product_id, product_data)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorResponse(error="NotFound", message="Product not found").model_dump())
    return product
