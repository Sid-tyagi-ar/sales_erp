from fastapi import APIRouter, Depends, HTTPException, status, Request
from app.schemas.purchase_receipt import PurchaseReceiptRequest, PurchaseReceiptResponse
from app.schemas.error import ErrorResponse
from app.services.purchase_receipt_service import PurchaseReceiptService

router = APIRouter(prefix="/purchase-receipts", tags=["Purchase Receipts"])

@router.post(
    "", # Changed from "/" to ""
    response_model=PurchaseReceiptResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def create_purchase_receipt(
    request: Request,
    pr_data: PurchaseReceiptRequest,
    pr_service: PurchaseReceiptService = Depends()
):
    try:
        tenant_id = request.state.tenant_id
        purchase_receipt = await pr_service.create(tenant_id, pr_data)
        return purchase_receipt
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorResponse(error="ValueError", message=str(e)).model_dump())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorResponse(error="ServerError", message=str(e)).model_dump())