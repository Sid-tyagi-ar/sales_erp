from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp
from app.schemas.error import ErrorResponse, ErrorDetail
from app.core.logger import get_logger

logger = get_logger("middleware.tenant")

class TenantMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        tenant_header = request.headers.get('X-Tenant-ID', 'none')
        logger.debug(
            f"→ {request.method} {request.url.path} | "
            f"tenant: {tenant_header}"
        )

        # Fix: Bypass tenant validation for OPTIONS preflight requests
        if request.method == "OPTIONS":
            logger.debug(f"Bypassing X-Tenant-ID validation for OPTIONS request: {request.url.path}")
            return await call_next(request)

        # Check if the path should be skipped
        if (
            request.url.path == "/health"
            or request.url.path.startswith("/docs")
            or request.url.path.startswith("/redoc")
            or request.url.path.startswith("/openapi")
            or request.url.path.startswith("/tenants") # This covers all /tenants routes
        ):
            response = await call_next(request)
            return response

        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            logger.warning(
                f"✗ Missing X-Tenant-ID | "
                f"{request.method} {request.url.path}"
            )
            error_response = ErrorResponse(
                error="Unauthorized",
                message="X-Tenant-ID header is required.",
                details=[ErrorDetail(field="X-Tenant-ID", message="Missing tenant identifier in headers.")]
            )
            return JSONResponse(status_code=400, content=error_response.model_dump())

        request.state.tenant_id = tenant_id
        logger.debug(
            f"✓ Tenant validated: {tenant_id}"
        )
        response = await call_next(request)
        return response
