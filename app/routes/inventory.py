from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List
from app.schemas.inventory import InventoryBalanceResponse
from app.schemas.error import ErrorResponse
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory"])

@router.get(
    "", # Changed from "/" to ""
    response_model=List[InventoryBalanceResponse],
    responses={500: {"model": ErrorResponse}}
)
async def list_inventory_balances(
    request: Request,
    inventory_service: InventoryService = Depends()
):
    try:
        tenant_id = request.state.tenant_id
        balances = await inventory_service.list(tenant_id)
        return balances
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorResponse(error="ServerError", message=str(e)).model_dump())
