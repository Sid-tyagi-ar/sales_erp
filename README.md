# Manufacturing ERP API

This project scaffolds a multi-tenant manufacturing inventory and order fulfillment engine using FastAPI and Firebase.

## Table of Contents
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup Instructions](#setup-instructions)
- [How to Run](#how-to-run)
- [Seed Script](#seed-script)
  - [How the Seed Script Works](#how-the-seed-script-works)
  - [Creating New Seed Scripts](#creating-new-seed-scripts)
- [API Endpoints](#api-endpoints)
- [Logging and Auditing](#logging-and-auditing)
- [CORS Configuration](#cors-configuration)

## Tech Stack
- Python 3.11+
- FastAPI
- Pydantic v2
- Firebase Admin SDK (Firestore)
- Uvicorn
- python-dotenv for environment management
- httpx for API calls in seed scripts

## Project Structure

```
manufacturing_erp/
├── app/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── audit.py
│   │   └── logger.py
│   ├── db/
│   │   ├── __init__.py
│   │   └── firebase.py
│   ├── enums.py
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── tenant.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── product.py
│   │   ├── warehouse.py
│   │   ├── customer.py
│   │   ├── bom.py
│   │   ├── inventory.py
│   │   ├── ledger.py
│   │   ├── purchase_receipt.py
│   │   ├── manufacturing_order.py
│   │   └── sales_order.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── tenant.py
│   │   ├── product.py
│   │   ├── warehouse.py
│   │   ├── customer.py
│   │   ├── bom.py
│   │   ├── inventory.py
│   │   ├── ledger.py
│   │   ├── purchase_receipt.py
│   │   ├── manufacturing_order.py
│   │   ├── sales_order.py
│   │   └── audit.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── tenant.py
│   │   ├── product.py
│   │   ├── warehouse.py
│   │   ├── customer.py
│   │   ├── bom.py
│   │   ├── inventory.py
│   │   ├── ledger.py
│   │   ├── purchase_receipt.py
│   │   ├── manufacturing_order.py
│   │   ├── sales_order.py
│   │   ├── error.py
│   │   └── audit.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── tenant_service.py
│   │   ├── product_service.py
│   │   ├── warehouse_service.py
│   │   ├── customer_service.py
│   │   ├── bom_service.py
│   │   ├── ledger_service.py
│   │   ├── inventory_service.py
│   │   ├── purchase_receipt_service.py
│   │   ├── manufacturing_service.py
│   │   └── sales_order_service.py
│   └── main.py
├── seed/
│   └── seed.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## Setup Instructions

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd manufacturing_erp
    ```

2.  **Create a Python Virtual Environment (optional but recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Firebase Project Setup:**
    *   Go to the Firebase Console (console.firebase.google.com).
    *   Create a new Firebase project.
    *   Navigate to Project settings -> Service accounts.
    *   Generate a new private key and download the `serviceAccountKey.json` file.

5.  **Environment Variables:**
    *   Create a `.env` file in the root of the project based on `.env.example`:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file and update the following. You have two options for providing Firebase credentials:
        *   **Option 1: Using a file path (local development)**
            ```
            FIREBASE_CREDENTIALS_PATH=/path/to/your/serviceAccountKey.json
            FIREBASE_PROJECT_ID=your-firebase-project-id
            APP_ENV=development
            ```
            Replace `/path/to/your/serviceAccountKey.json` with the actual absolute path to your downloaded Firebase service account key.
        *   **Option 2: Using JSON string directly (production/CI/CD)**
            ```
            FIREBASE_CREDENTIALS_JSON={"type": "service_account", "project_id": "...", "private_key_id": "...", "private_key": "...", "client_email": "...", "client_id": "...", "auth_uri": "...", "token_uri": "...", "auth_provider_x509_cert_url": "...", "client_x509_cert_url": "...", "universe_domain": "..."}
            FIREBASE_PROJECT_ID=your-firebase-project-id
            APP_ENV=production
            ```
            Replace the entire JSON string with the content of your `serviceAccountKey.json` file. Ensure it's a single line without newlines if setting in some environments.
            **Note:** If both `FIREBASE_CREDENTIALS_JSON` and `FIREBASE_CREDENTIALS_PATH` are set, `FIREBASE_CREDENTIALS_JSON` will take precedence.

## How to Run

1.  **Start the FastAPI application:**
    ```bash
    uvicorn app.main:app --reload
    ```
    The API will be accessible at `http://localhost:8000`.

2.  **Access API Documentation:**
    *   Swagger UI: `http://localhost:8000/docs`
    *   ReDoc: `http://localhost:8000/redoc`

## Seed Script

The `seed/seed.py` script is designed to populate your Firebase Firestore with initial data for testing and demonstration purposes. It calls the live API endpoints in a strict, sequential order. If any API call fails, the script will print an error and stop execution.

### How the Seed Script Works

The script performs the following steps:

1.  **Health Check:** Verifies that the FastAPI server is running and responsive.
2.  **Create Tenants:** Creates two tenants, "Tenant Alpha" and "Tenant Beta", and stores their generated IDs.
3.  **Create Warehouses:** For each tenant, creates a "Main Warehouse" and a "Secondary Warehouse".
4.  **Create Products:** For each tenant, creates a set of raw materials, finished goods, and trading goods.
5.  **Create Customers:** For each tenant, creates two sample customers.
6.  **Purchase Receipts:** For each tenant, simulates a purchase receipt of raw materials into their main warehouse.
7.  **Verify Inventory After Receipt:** Fetches and displays the updated inventory balances for the received raw materials.
8.  **Define BOM for CNC Machine:** For each tenant, defines a Bill of Materials for the "CNC Machine" finished good.
9.  **Manufacture CNC Machines:** For each tenant, creates a manufacturing order for 10 "CNC Machines" and then attempts to complete it. It reports success or any shortages encountered.
10. **Verify Inventory After Manufacture:** Fetches and displays the inventory balances, showing reduced raw materials and increased finished goods.
11. **Create Sales Order:** For "Tenant Alpha", creates a sales order for 8 "CNC Machines".
12. **Confirm Sales Order:** Confirms the sales order, which reserves the stock in inventory. The script then verifies the reserved quantities.
13. **Test Insufficient Stock:** Attempts to create and confirm another sales order for "Tenant Alpha" that would exceed available stock. This step is expected to fail, and the script verifies that the API correctly rejects it with an "INSUFFICIENT_STOCK_FOR_CONFIRMATION" error.
14. **Dispatch First Order:** Dispatches the first sales order for "Tenant Alpha", reducing on-hand and reserved quantities.
15. **Check Ledger:** Fetches and displays the latest stock ledger entries for "Tenant Alpha", showing all movements.
16. **Check Audit Log:** Fetches and displays the latest audit log entries for "Tenant Alpha", demonstrating the recorded events.

To run the seed script:
```bash
python seed/seed.py
```
**Important:** Ensure your FastAPI server is running (`uvicorn app.main:app --reload`) before executing the seed script.

### Creating New Seed Scripts

You can create new seed scripts or modify the existing one to test different scenarios. Follow these guidelines:

1.  **Duplicate `seed/seed.py`:** It's recommended to copy `seed/seed.py` to a new file (e.g., `seed/test_scenario_1.py`) to avoid overwriting the main seed data.
2.  **Use Helper Functions:** Leverage the `post` and `get` async helper functions provided in `seed/seed.py` for making API calls.
3.  **Handle Tenant IDs:** Remember that most API calls require an `X-Tenant-ID` header. You'll need to create tenants first and use their IDs.
4.  **Error Handling:** The helper functions include basic error handling. If you need more specific error checks (e.g., expecting a 400 status code), you'll need to implement custom `httpx` calls as shown in `STEP 13` of the main seed script.
5.  **Run Independently:** You can run your new seed script using `python seed/your_new_script.py`.

Example of a new seed script structure:

```python
import httpx
import asyncio
import os
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

# Load environment variables from .env file
load_dotenv()

BASE_URL = "http://localhost:8000"

# Re-use helper functions from seed.py or define them here
async def post(client: httpx.AsyncClient, path: str, body: Dict, tenant_id: Optional[str] = None) -> Dict:
    # ... (copy from seed/seed.py)
    pass

async def get(client: httpx.AsyncClient, path: str, tenant_id: Optional[str] = None) -> Any:
    # ... (copy from seed/seed.py)
    pass

async def my_new_seed_scenario():
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        print("\n── My New Seed Scenario ──")
        
        # Example: Create a new tenant
        new_tenant = await post(client, "/tenants", {"name": "Test Tenant", "email": "test@example.com"})
        new_tenant_id = new_tenant["id"]
        print(f"  Created Test Tenant: {new_tenant_id}")

        # Example: Create a product for the new tenant
        product_data = {
            "name": "Test Product",
            "sku": "TEST-PROD-001",
            "type": "raw_material",
            "unit_of_measure": "unit",
            "standard_cost": 10.0,
            "selling_price": 15.0,
            "sellable": False
        }
        test_product = await post(client, "/products", product_data, new_tenant_id)
        print(f"  Created Test Product: {test_product['id']}")

        print("\n✓ New seed scenario completed.")

if __name__ == "__main__":
    import asyncio
    print("Starting new seed scenario...")
    print("Make sure server is running on localhost:8000")
    try:
        asyncio.run(my_new_seed_scenario())
    except Exception as e:
        print(f"\n✗ NEW SEED SCENARIO FAILED: {e}")
        exit(1)
```

## API Endpoints

The API exposes the following main endpoints (details available in Swagger UI at `/docs`):

*   `/health`: Health check endpoint.
*   `/tenants`: Manage tenant creation, retrieval, update, and soft deletion.
*   `/products`: Manage product creation, retrieval, update, and listing.
*   `/warehouses`: Manage warehouse creation, retrieval, update, and listing.
*   `/customers`: Manage customer creation, retrieval, and listing.
*   `/bom`: Manage Bill of Materials creation and retrieval.
*   `/purchase-receipts`: Create purchase receipts.
*   `/manufacturing-orders`: Create and complete manufacturing orders.
*   `/sales-orders`: Create, confirm, dispatch, and cancel sales orders.
*   `/inventory`: View inventory balances.
*   `/stock-ledger`: View stock ledger entries.
*   `/audit-log`: View audit trail entries.

## Logging and Auditing

The application implements structured logging using Python's `logging` module, configured to output to `sys.stdout`. Log levels (DEBUG, INFO, WARNING, ERROR) are used appropriately to indicate the severity and nature of events.

An `AuditService` is integrated to record significant business events (e.g., product creation, stock movements, order confirmations) to a dedicated `audit_log` collection in Firestore. This provides an immutable audit trail for all critical operations. Audit failures are designed to be non-blocking, ensuring the main application flow continues even if an audit log entry cannot be written.

## CORS Configuration

The application is configured with `CORSMiddleware` to handle Cross-Origin Resource Sharing. For testing purposes, `allow_origins` is set to `["*"]` (allowing all origins). `allow_credentials`, `allow_methods`, and `allow_headers` are also set to allow broad access. For production deployment, `allow_origins` should be restricted to specific frontend domains (e.g., `["https://your-frontend.com"]`). The tenant middleware is configured to bypass `X-Tenant-ID` validation for `OPTIONS` preflight requests.
