from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp
from app.schemas.error import ErrorResponse, ErrorDetail

class TenantMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.EXCLUDE_PATHS = [
            "/docs",
            "/redoc",
            "/openapi.json"
        ]

    async def dispatch(self, request: Request, call_next):
        # Skip middleware for documentation paths
        if request.url.path in self.EXCLUDE_PATHS:
            response = await call_next(request)
            return response
        
        # Skip middleware for POST /tenants
        if request.url.path == "/tenants" and request.method == "POST":
            response = await call_next(request)
            return response

        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            error_response = ErrorResponse(
                error="Unauthorized",
                message="X-Tenant-ID header is required.",
                details=[ErrorDetail(field="X-Tenant-ID", message="Missing tenant identifier in headers.")]
            )
            return JSONResponse(status_code=400, content=error_response.model_dump())

        request.state.tenant_id = tenant_id
        response = await call_next(request)
        return response