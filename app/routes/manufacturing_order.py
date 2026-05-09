from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.schemas.manufacturing_order import ManufacturingOrderRequest, ManufacturingOrderResponse, ManufacturingCompleteResponse
from app.schemas.error import ErrorResponse
from app.services.manufacturing_service import ManufacturingService

router = APIRouter(prefix="/manufacturing-orders", tags=["Manufacturing Orders"])

@router.post(
    "", # Changed from "/" to ""
    response_model=ManufacturingOrderResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def create_manufacturing_order(
    request: Request,
    mo_data: ManufacturingOrderRequest,
    mfg_service: ManufacturingService = Depends()
):
    try:
        tenant_id = request.state.tenant_id
        manufacturing_order = await mfg_service.create_order(tenant_id, mo_data)
        return manufacturing_order
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorResponse(error="ValueError", message=str(e)).model_dump())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorResponse(error="ServerError", message=str(e)).model_dump())

@router.get(
    "/{order_id}",
    response_model=ManufacturingOrderResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def get_manufacturing_order(
    request: Request,
    order_id: str,
    mfg_service: ManufacturingService = Depends()
):
    try:
        tenant_id = request.state.tenant_id
        manufacturing_order = await mfg_service.get(tenant_id, order_id)
        return manufacturing_order
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorResponse(error="ServerError", message=str(e)).model_dump())

@router.post(
    "/{order_id}/complete",
    response_model=ManufacturingCompleteResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def complete_manufacturing_order(
    request: Request,
    order_id: str,
    mfg_service: ManufacturingService = Depends()
):
    try:
        tenant_id = request.state.tenant_id
        result = await mfg_service.complete_order(tenant_id, order_id)
        if not result.can_complete and not result.success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorResponse(error="BadRequest", message="Cannot complete manufacturing order due to shortages or other issues.", details=[d.model_dump() for d in result.shortages]).model_dump())
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorResponse(error="ValueError", message=str(e)).model_dump())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorResponse(error="ServerError", message=str(e)).model_dump())
