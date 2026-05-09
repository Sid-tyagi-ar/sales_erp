from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List
from app.schemas.ledger import StockLedgerResponse
from app.schemas.error import ErrorResponse
from app.services.ledger_service import LedgerService

router = APIRouter(prefix="/stock-ledger", tags=["Stock Ledger"])

@router.get(
    "/",
    response_model=List[StockLedgerResponse],
    responses={500: {"model": ErrorResponse}}
)
async def list_stock_ledger_entries(
    request: Request,
    ledger_service: LedgerService = Depends()
):
    try:
        tenant_id = request.state.tenant_id
        entries = await ledger_service.list(tenant_id, filters={}) # Pass empty filters for now
        return entries
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorResponse(error="ServerError", message=str(e)).model_dump())
