from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List
from app.schemas.warehouse import WarehouseCreateRequest, WarehouseUpdateRequest, WarehouseResponse
from app.schemas.error import ErrorResponse
from app.services.warehouse_service import WarehouseService

router = APIRouter(prefix="/warehouses", tags=["Warehouses"])

@router.post(
    "", # Changed from "/" to ""
    response_model=WarehouseResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def create_warehouse(
    request: Request,
    warehouse_data: WarehouseCreateRequest,
    warehouse_service: WarehouseService = Depends()
):
    try:
        tenant_id = request.state.tenant_id
        warehouse = await warehouse_service.create(tenant_id, warehouse_data)
        return warehouse
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorResponse(error="ValueError", message=str(e)).model_dump())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorResponse(error="ServerError", message=str(e)).model_dump())

@router.get(
    "/",
    response_model=List[WarehouseResponse],
    responses={500: {"model": ErrorResponse}}
)
async def list_warehouses(
    request: Request,
    warehouse_service: WarehouseService = Depends()
):
    try:
        tenant_id = request.state.tenant_id
        warehouses = await warehouse_service.list(tenant_id)
        return warehouses
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorResponse(error="ServerError", message=str(e)).model_dump())

@router.get(
    "/{warehouse_id}",
    response_model=WarehouseResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def get_warehouse(
    request: Request,
    warehouse_id: str,
    warehouse_service: WarehouseService = Depends()
):
    tenant_id = request.state.tenant_id
    warehouse = await warehouse_service.get(tenant_id, warehouse_id)
    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorResponse(error="NotFound", message="Warehouse not found").model_dump())
    return warehouse

@router.put(
    "/{warehouse_id}",
    response_model=WarehouseResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def update_warehouse(
    request: Request,
    warehouse_id: str,
    warehouse_data: WarehouseUpdateRequest,
    warehouse_service: WarehouseService = Depends()
):
    tenant_id = request.state.tenant_id
    warehouse = await warehouse_service.update(tenant_id, warehouse_id, warehouse_data)
    if not warehouse:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorResponse(error="NotFound", message="Warehouse not found").model_dump())
    return warehouse