from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.tenant import TenantCreateRequest, TenantResponse
from app.schemas.error import ErrorResponse
from app.services.tenant_service import TenantService

router = APIRouter(prefix="/tenants", tags=["Tenants"])

@router.post(
    "", # Changed from "/"
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}}
)
async def create_tenant(
    request: TenantCreateRequest,
    tenant_service: TenantService = Depends()
):
    try:
        tenant = await tenant_service.create(request)
        return tenant
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorResponse(error="ValueError", message=str(e)).model_dump())
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorResponse(error="ServerError", message=str(e)).model_dump())

@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def get_tenant(
    tenant_id: str,
    tenant_service: TenantService = Depends()
):
    tenant = await tenant_service.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorResponse(error="NotFound", message="Tenant not found").model_dump())
    return tenant

@router.put(
    "/{tenant_id}",
    response_model=TenantResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def update_tenant(
    tenant_id: str,
    request: dict, # Use dict for now, will define specific schema later if needed
    tenant_service: TenantService = Depends()
):
    tenant = await tenant_service.update(tenant_id, request)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorResponse(error="NotFound", message="Tenant not found").model_dump())
    return tenant

@router.delete(
    "/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def delete_tenant(
    tenant_id: str,
    tenant_service: TenantService = Depends()
):
    success = await tenant_service.delete(tenant_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorResponse(error="NotFound", message="Tenant not found").model_dump())
    return