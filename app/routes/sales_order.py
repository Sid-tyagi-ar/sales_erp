from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.schemas.sales_order import SalesOrderCreateRequest, SalesOrderResponse, DispatchRequest
from app.schemas.error import ErrorResponse
from app.services.sales_order_service import SalesOrderService

router = APIRouter(prefix="/sales-orders", tags=["Sales Orders"])

@router.post(
    "/",
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
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorResponse(error="ValueError", message=str(e)).model_dump())
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
        if not sales_order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorResponse(error="NotFound", message="Sales Order not found").model_dump())
        return sales_order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorResponse(error="ValueError", message=str(e)).model_dump())
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
        if not sales_order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorResponse(error="NotFound", message="Sales Order not found").model_dump())
        return sales_order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorResponse(error="ValueError", message=str(e)).model_dump())
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
        if not sales_order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorResponse(error="NotFound", message="Sales Order not found").model_dump())
        return sales_order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorResponse(error="ValueError", message=str(e)).model_dump())
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorResponse(error="ServerError", message=str(e)).model_dump())
