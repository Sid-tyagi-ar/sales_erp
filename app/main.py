from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import settings
from app.middleware.tenant import TenantMiddleware
from app.routes import tenant, product, warehouse, customer, bom, purchase_receipt, manufacturing_order, sales_order, inventory, ledger, audit # Import audit router

app = FastAPI(
    title="Manufacturing ERP API",
    redirect_slashes=False # Fix 1: Disable automatic trailing slash redirection
)

# Add Tenant Middleware
app.add_middleware(TenantMiddleware)

# Include Routers
app.include_router(tenant.router)
app.include_router(product.router)
app.include_router(warehouse.router)
app.include_router(customer.router)
app.include_router(bom.router)
app.include_router(purchase_receipt.router)
app.include_router(manufacturing_order.router)
app.include_router(sales_order.router)
app.include_router(inventory.router)
app.include_router(ledger.router)
app.include_router(audit.router) # Include audit router

@app.get("/health", tags=["Health Check"])
async def health_check():
    return {"status": "ok", "env": settings.APP_ENV}