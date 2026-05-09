from fastapi import APIRouter, Depends, HTTPException, status, Request
from typing import List
from app.schemas.customer import CustomerCreateRequest, CustomerResponse
from app.schemas.error import ErrorResponse
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/customers", tags=["Customers"])

@router.post(
    "/",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
)
async def create_customer(
    request: Request,
    customer_data: CustomerCreateRequest,
    customer_service: CustomerService = Depends()
):
    try:
        tenant_id = request.state.tenant_id
        customer = await customer_service.create(tenant_id, customer_data)
        return customer
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=ErrorResponse(error="ValueError", message=str(e)).model_dump())
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorResponse(error="ServerError", message=str(e)).model_dump())

@router.get(
    "/",
    response_model=List[CustomerResponse],
    responses={500: {"model": ErrorResponse}}
)
async def list_customers(
    request: Request,
    customer_service: CustomerService = Depends()
):
    try:
        tenant_id = request.state.tenant_id
        customers = await customer_service.list(tenant_id)
        return customers
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=ErrorResponse(error="ServerError", message=str(e)).model_dump())
