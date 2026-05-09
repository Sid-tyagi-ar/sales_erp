from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.schemas.bom import BOMCreateRequest, BOMResponse
from app.schemas.error import ErrorResponse
from app.services.bom_service import BOMService

router = APIRouter(prefix="/bom", tags=["Bill of Materials"])

@router.post(
    "", # Changed from "/" to ""
    response_model=BOMResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def create_bom(
    request: Request,
    bom_data: BOMCreateRequest,
    bom_service: BOMService = Depends()
):
    try:
        tenant_id = request.state.tenant_id
        bom = await bom_service.create(tenant_id, bom_data)
        return bom
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorResponse(error="ValueError", message=str(e)).model_dump())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorResponse(error="ServerError", message=str(e)).model_dump())

@router.get(
    "/{finished_good_sku}",
    response_model=BOMResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def get_bom(
    request: Request,
    finished_good_sku: str,
    bom_service: BOMService = Depends()
):
    tenant_id = request.state.tenant_id
    bom = await bom_service.get(tenant_id, finished_good_sku)
    if not bom:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=ErrorResponse(error="NotFound", message="BOM not found").model_dump())
    return bom