from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from typing import List, Optional
from app.schemas.ledger import StockLedgerResponse
from app.schemas.error import ErrorResponse
from app.services.ledger_service import LedgerService
from app.enums import MovementType # Import MovementType for query param

router = APIRouter(prefix="/stock-ledger", tags=["Stock Ledger"])

@router.get(
    "",
    response_model=List[StockLedgerResponse],
    responses={500: {"model": ErrorResponse}}
)
async def list_stock_ledger_entries(
    request: Request,
    warehouse_id: Optional[str] = Query(None, description="Filter by warehouse ID"),
    product_id: Optional[str] = Query(None, description="Filter by product ID"),
    movement_type: Optional[MovementType] = Query(None, description="Filter by movement type"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of ledger entries to return"),
    ledger_service: LedgerService = Depends()
):
    try:
        tenant_id = request.state.tenant_id
        entries = await ledger_service.list(
            tenant_id=tenant_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
            movement_type=movement_type,
            limit=limit
        )
        return entries
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="ServerError",
                message=str(e)
            ).model_dump()
        )
