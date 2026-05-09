from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List, Optional
from app.schemas.sales_order import SalesOrderCreateRequest, SalesOrderResponse, DispatchRequest
from app.schemas.error import ErrorResponse
from app.enums import OrderStatus
from app.services.sales_order_service import SalesOrderService

router = APIRouter(prefix="/sales-orders", tags=["Sales Orders"])

@router.post(
    "", # Changed from "/" to ""
    response_model=SalesOrderResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def create_sales_order(
    request: Request,
    so_data: SalesOrderCreateRequest,
    so_service: SalesOrderService = Depends()
):
    try:
        tenant_id = request.state.tenant_id
        sales_order = await so_service.create(tenant_id, so_data)
        return sales_order
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorResponse(error="ServerError", message=str(e)).model_dump())

@router.get(
    "", # Changed from "/" to ""
    response_model=List[SalesOrderResponse],
    responses={500: {"model": ErrorResponse}}
)
async def list_sales_orders(
    request: Request,
    status: Optional[OrderStatus] = None,
    so_service: SalesOrderService = Depends()
):
    try:
        tenant_id = request.state.tenant_id
        sales_orders = await so_service.list(tenant_id, status_filter=status)
        return sales_orders
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorResponse(error="ServerError", message=str(e)).model_dump())

@router.get(
    "/{order_id}",
    response_model=SalesOrderResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def get_sales_order(
    request: Request,
    order_id: str,
    so_service: SalesOrderService = Depends()
):
    try:
        tenant_id = request.state.tenant_id
        sales_order = await so_service.get(tenant_id, order_id)
        return sales_order
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorResponse(error="ServerError", message=str(e)).model_dump())

@router.post(
    "/{order_id}/confirm",
    response_model=SalesOrderResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def confirm_sales_order(
    request: Request,
    order_id: str,
    so_service: SalesOrderService = Depends()
):
    try:
        tenant_id = request.state.tenant_id
        sales_order = await so_service.confirm(tenant_id, order_id)
        return sales_order
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorResponse(error="ServerError", message=str(e)).model_dump())

@router.post(
    "/{order_id}/dispatch",
    response_model=SalesOrderResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def dispatch_sales_order(
    request: Request,
    order_id: str,
    dispatch_data: DispatchRequest,
    so_service: SalesOrderService = Depends()
):
    try:
        tenant_id = request.state.tenant_id
        sales_order = await so_service.dispatch(tenant_id, order_id, dispatch_data)
        return sales_order
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorResponse(error="ServerError", message=str(e)).model_dump())

@router.post(
    "/{order_id}/cancel",
    response_model=SalesOrderResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def cancel_sales_order(
    request: Request,
    order_id: str,
    so_service: SalesOrderService = Depends()
):
    try:
        tenant_id = request.state.tenant_id
        sales_order = await so_service.cancel(tenant_id, order_id)
        return sales_order
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorResponse(error="ServerError", message=str(e)).model_dump())
