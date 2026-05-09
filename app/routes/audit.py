from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from typing import List, Dict, Any, Optional
from datetime import datetime
# from pydantic import BaseModel # No longer needed here as AuditEntryResponse is imported
from app.schemas.error import ErrorResponse
from app.db.firebase import get_db
from firebase_admin import firestore
from firebase_admin.firestore import AsyncQuery
from app.schemas.audit import AuditEntryResponse # Import from schemas

router = APIRouter(prefix="/audit-log", tags=["Audit Log"])

@router.get(
    "", # Changed from "/" to ""
    response_model=List[AuditEntryResponse],
    responses={500: {"model": ErrorResponse}}
)
async def list_audit_log(
    request: Request,
    entity_type: Optional[str] = Query(None, description="Filter by entity type (e.g., 'product', 'sales_order')"),
    event_type: Optional[str] = Query(None, description="Filter by event type (e.g., 'PRODUCT_CREATED', 'STOCK_RECEIVED')"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of audit entries to return"),
):
    try:
        db = get_db()
        tenant_id = request.state.tenant_id
        
        query_ref: AsyncQuery = db.collection("tenants").document(tenant_id).collection("audit_log")
        
        if entity_type:
            query_ref = query_ref.where("entity_type", "==", entity_type)
        if event_type:
            query_ref = query_ref.where("event_type", "==", event_type)
        
        query_ref = query_ref.order_by("created_at", direction=firestore.Query.DESCENDING).limit(limit)
        
        docs = await query_ref.get()
        
        audit_entries = [AuditEntryResponse(**doc.to_dict()) for doc in docs] # Convert to Pydantic model
        
        return audit_entries
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(error="ServerError", message=f"An unexpected error occurred: {e}").model_dump()
        )
