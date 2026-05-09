import httpx
import asyncio
import os
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables from .env file
load_dotenv()

BASE_URL = "http://localhost:8000"

async def call_api(method: str, path: str, json_data: Dict = None, headers: Dict = None) -> Dict:
    async with httpx.AsyncClient() as client:
        url = f"{BASE_URL}{path}"
        print(f"Calling {method} {url} with data: {json_data} and headers: {headers}")
        response = await client.request(method, url, json=json_data, headers=headers)
        response.raise_for_status()  # Raise an exception for 4xx or 5xx status codes
        return response.json()

async def seed_data():
    print("Starting data seeding...")

    # 1. Create 2 tenants
    print("\n--- Creating Tenants ---")
    tenant_alpha_data = {"name": "Tenant Alpha", "email": "alpha@erp.com"}
    tenant_beta_data = {"name": "Tenant Beta", "email": "beta@erp.com"}

    tenant_alpha = await call_api("POST", "/tenants", json_data=tenant_alpha_data)
    print(f"Created Tenant Alpha: {tenant_alpha}")
    tenant_beta = await call_api("POST", "/tenants", json_data=tenant_beta_data)
    print(f"Created Tenant Beta: {tenant_beta}")

    tenants = [
        {"id": tenant_alpha["id"], "name": tenant_alpha["name"], "headers": {"X-Tenant-ID": tenant_alpha["id"]}},
        {"id": tenant_beta["id"], "name": tenant_beta["name"], "headers": {"X-Tenant-ID": tenant_beta["id"]}},
    ]

    for tenant in tenants:
        print(f"\n--- Seeding data for {tenant['name']} (ID: {tenant['id']}) ---")
        headers = tenant["headers"]

        # 2. For each tenant create 2 warehouses
        print("\n--- Creating Warehouses ---")
        main_warehouse_data = {"name": "Main Warehouse", "code": "MAIN", "city": "Anytown"}
        sec_warehouse_data = {"name": "Secondary Warehouse", "code": "SEC", "city": "Othertown"}

        main_warehouse = await call_api("POST", "/warehouses", json_data=main_warehouse_data, headers=headers)
        print(f"Created Main Warehouse: {main_warehouse}")
        sec_warehouse = await call_api("POST", "/warehouses", json_data=sec_warehouse_data, headers=headers)
        print(f"Created Secondary Warehouse: {sec_warehouse}")

        # 3. For each tenant create products
        print("\n--- Creating Products ---")
        products_to_create = [
            {"name": "Steel Plate", "sku": "RM-STEEL-001", "type": "raw_material", "unit_of_measure": "kg", "standard_cost": 50.0, "selling_price": 75.0},
            {"name": "Motor", "sku": "RM-MOTOR-001", "type": "raw_material", "unit_of_measure": "unit", "standard_cost": 200.0, "selling_price": 300.0},
            {"name": "Control Panel", "sku": "RM-CP-001", "type": "raw_material", "unit_of_measure": "unit", "standard_cost": 150.0, "selling_price": 225.0},
            {"name": "CNC Machine", "sku": "FG-CNC-001", "type": "finished_good", "unit_of_measure": "unit", "standard_cost": 1000.0, "selling_price": 1500.0},
            {"name": "Hydraulic Press", "sku": "FG-HP-001", "type": "finished_good", "unit_of_measure": "unit", "standard_cost": 2000.0, "selling_price": 3000.0},
            {"name": "Safety Kit", "sku": "TG-SK-001", "type": "trading_good", "unit_of_measure": "unit", "standard_cost": 50.0, "selling_price": 80.0},
        ]
        created_products = {}
        for product_data in products_to_create:
            product = await call_api("POST", "/products", json_data=product_data, headers=headers)
            print(f"Created Product: {product}")
            created_products[product["sku"]] = product

        # 4. For each tenant create 2 customers
        print("\n--- Creating Customers ---")
        customer1_data = {"name": "Customer One", "email": f"customer1_{tenant['id']}@example.com", "phone": "111-222-3333"}
        customer2_data = {"name": "Customer Two", "email": f"customer2_{tenant['id']}@example.com", "phone": "444-555-6666"}

        customer1 = await call_api("POST", "/customers", json_data=customer1_data, headers=headers)
        print(f"Created Customer 1: {customer1}")
        customer2 = await call_api("POST", "/customers", json_data=customer2_data, headers=headers)
        print(f"Created Customer 2: {customer2}")

        # 5. For each tenant POST purchase receipts to MAIN warehouse
        print("\n--- Creating Purchase Receipts ---")
        pr_items = [
            {"sku": "RM-STEEL-001", "quantity": 100.0, "unit_cost": 50.0},
            {"sku": "RM-MOTOR-001", "quantity": 20.0, "unit_cost": 200.0},
            {"sku": "RM-CP-001", "quantity": 20.0, "unit_cost": 150.0},
        ]
        purchase_receipt_data = {"warehouse_id": main_warehouse["id"], "items": pr_items}
        purchase_receipt = await call_api("POST", "/purchase-receipts", json_data=purchase_receipt_data, headers=headers)
        print(f"Created Purchase Receipt: {purchase_receipt}")

        # 6. For each tenant create BOM for CNC Machine
        print("\n--- Creating BOM for CNC Machine ---")
        cnc_bom_data = {
            "finished_good_sku": "FG-CNC-001",
            "components": [
                {"raw_material_sku": "RM-STEEL-001", "quantity_required": 5.0, "wastage_percent": 0.0},
                {"raw_material_sku": "RM-MOTOR-001", "quantity_required": 1.0, "wastage_percent": 0.0},
                {"raw_material_sku": "RM-CP-001", "quantity_required": 1.0, "wastage_percent": 0.0},
            ]
        }
        cnc_bom = await call_api("POST", "/bom", json_data=cnc_bom_data, headers=headers)
        print(f"Created BOM for CNC Machine: {cnc_bom}")

    print("\nData seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed_data())
