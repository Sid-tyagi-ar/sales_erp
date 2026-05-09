import httpx
import asyncio
from typing import Dict, Any, Optional

BASE_URL = "https://saleserp-production-e9b3.up.railway.app"


async def post(
    client: httpx.AsyncClient,
    path: str,
    body: Dict,
    tenant_id: Optional[str] = None
) -> Dict:
    headers = {}

    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id

    response = await client.post(
        f"{BASE_URL}{path}",
        json=body,
        headers=headers
    )

    if response.status_code not in [200, 201]:
        print(f"\n✗ FAILED POST {path}")
        print(f"Status: {response.status_code}")
        print(f"Body: {response.text}")
        raise Exception(f"POST failed: {path}")

    print(f"✓ POST {path}")
    return response.json()


async def get(
    client: httpx.AsyncClient,
    path: str,
    tenant_id: Optional[str] = None
) -> Any:
    headers = {}

    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id

    response = await client.get(
        f"{BASE_URL}{path}",
        headers=headers
    )

    if response.status_code != 200:
        print(f"\n✗ FAILED GET {path}")
        print(f"Status: {response.status_code}")
        print(f"Body: {response.text}")
        raise Exception(f"GET failed: {path}")

    print(f"✓ GET {path}")
    return response.json()


async def seed():

    async with httpx.AsyncClient(
        timeout=60,
        follow_redirects=True
    ) as client:

        print("\n==============================")
        print("SEED V2 STARTING")
        print("==============================")

        # -------------------------------
        # HEALTH CHECK
        # -------------------------------

        print("\n── Health Check ──")

        try:
            health = await get(client, "/health")
            print(f"Server Status: {health}")
        except:
            print("Health endpoint missing, continuing...")


        # -------------------------------
        # CREATE TENANTS
        # -------------------------------

        print("\n── Create Tenants ──")

        tenant_orion = await post(
            client,
            "/tenants",
            {
                "name": "Tenant Orion Manufacturing",
                "email": "orion.manufacturing@erp.com"
            }
        )

        tenant_nova = await post(
            client,
            "/tenants",
            {
                "name": "Tenant Nova Industries",
                "email": "nova.industries@erp.com"
            }
        )

        orion_id = tenant_orion["id"]
        nova_id = tenant_nova["id"]

        print(f"Orion Tenant ID: {orion_id}")
        print(f"Nova Tenant ID:  {nova_id}")


        # -------------------------------
        # CREATE WAREHOUSES
        # -------------------------------

        print("\n── Create Warehouses ──")

        # ORION

        orion_main = await post(
            client,
            "/warehouses",
            {
                "name": "Orion Central Warehouse",
                "code": "ORION-MAIN",
                "city": "Bangalore"
            },
            orion_id
        )

        orion_sec = await post(
            client,
            "/warehouses",
            {
                "name": "Orion Secondary Warehouse",
                "code": "ORION-SEC",
                "city": "Hyderabad"
            },
            orion_id
        )

        # NOVA

        nova_main = await post(
            client,
            "/warehouses",
            {
                "name": "Nova Primary Hub",
                "code": "NOVA-MAIN",
                "city": "Pune"
            },
            nova_id
        )

        nova_sec = await post(
            client,
            "/warehouses",
            {
                "name": "Nova Reserve Hub",
                "code": "NOVA-SEC",
                "city": "Chennai"
            },
            nova_id
        )

        print("Warehouses created.")


        # -------------------------------
        # CREATE PRODUCTS
        # -------------------------------

        print("\n── Create Products ──")

        products = [
            {
                "name": "Titanium Sheet",
                "sku": "RM-TI-001",
                "type": "raw_material",
                "unit_of_measure": "kg",
                "standard_cost": 120.0,
                "selling_price": 0.0,
                "sellable": False
            },
            {
                "name": "Servo Motor",
                "sku": "RM-SERVO-001",
                "type": "raw_material",
                "unit_of_measure": "unit",
                "standard_cost": 350.0,
                "selling_price": 0.0,
                "sellable": False
            },
            {
                "name": "Sensor Module",
                "sku": "RM-SENSOR-001",
                "type": "raw_material",
                "unit_of_measure": "unit",
                "standard_cost": 180.0,
                "selling_price": 0.0,
                "sellable": False
            },
            {
                "name": "Autonomous Welding Robot",
                "sku": "FG-AWR-001",
                "type": "finished_good",
                "unit_of_measure": "unit",
                "standard_cost": 8500.0,
                "selling_price": 12000.0,
                "sellable": True
            },
            {
                "name": "Industrial Laser Cutter",
                "sku": "FG-LASER-001",
                "type": "finished_good",
                "unit_of_measure": "unit",
                "standard_cost": 15000.0,
                "selling_price": 21000.0,
                "sellable": True
            },
            {
                "name": "Factory Safety Helmet",
                "sku": "TG-HELMET-001",
                "type": "trading_good",
                "unit_of_measure": "unit",
                "standard_cost": 25.0,
                "selling_price": 60.0,
                "sellable": True
            }
        ]

        for product in products:
            await post(client, "/products", product, orion_id)

        for product in products:
            await post(client, "/products", product, nova_id)

        print("Products created.")


        # -------------------------------
        # CREATE CUSTOMERS
        # -------------------------------

        print("\n── Create Customers ──")

        orion_customer = await post(
            client,
            "/customers",
            {
                "name": "Apex Robotics",
                "email": "orders@apexrobotics.com",
                "phone": "9999991111",
                "address": "Electronic City, Bangalore"
            },
            orion_id
        )

        nova_customer = await post(
            client,
            "/customers",
            {
                "name": "Titan Manufacturing",
                "email": "procurement@titanmanufacturing.com",
                "phone": "9999992222",
                "address": "Industrial Area, Pune"
            },
            nova_id
        )

        print("Customers created.")


        # -------------------------------
        # PURCHASE RECEIPTS
        # -------------------------------

        print("\n── Purchase Receipts ──")

        receipt_body = {
            "warehouse_id": orion_main["id"],
            "items": [
                {
                    "sku": "RM-TI-001",
                    "quantity": 200,
                    "unit_cost": 120.0
                },
                {
                    "sku": "RM-SERVO-001",
                    "quantity": 30,
                    "unit_cost": 350.0
                },
                {
                    "sku": "RM-SENSOR-001",
                    "quantity": 50,
                    "unit_cost": 180.0
                }
            ]
        }

        await post(
            client,
            "/purchase-receipts",
            receipt_body,
            orion_id
        )

        receipt_body["warehouse_id"] = nova_main["id"]

        await post(
            client,
            "/purchase-receipts",
            receipt_body,
            nova_id
        )

        print("Purchase receipts completed.")


        # -------------------------------
        # CREATE BOM
        # -------------------------------

        print("\n── Create BOM ──")

        bom_body = {
            "finished_good_sku": "FG-AWR-001",
            "components": [
                {
                    "raw_material_sku": "RM-TI-001",
                    "quantity_required": 8.0,
                    "wastage_percent": 1.5
                },
                {
                    "raw_material_sku": "RM-SERVO-001",
                    "quantity_required": 2.0,
                    "wastage_percent": 0.0
                },
                {
                    "raw_material_sku": "RM-SENSOR-001",
                    "quantity_required": 4.0,
                    "wastage_percent": 0.0
                }
            ]
        }

        await post(client, "/bom", bom_body, orion_id)
        await post(client, "/bom", bom_body, nova_id)

        print("BOM created.")


        # -------------------------------
        # MANUFACTURING
        # -------------------------------

        print("\n── Manufacturing Orders ──")

        manufacturing_body = {
            "warehouse_id": orion_main["id"],
            "finished_good_sku": "FG-AWR-001",
            "quantity_to_produce": 5
        }

        mfg_order = await post(
            client,
            "/manufacturing-orders",
            manufacturing_body,
            orion_id
        )

        mfg_id = mfg_order["id"]

        completion = await post(
            client,
            f"/manufacturing-orders/{mfg_id}/complete",
            {},
            orion_id
        )

        print("Manufacturing completed.")
        print(completion)


        # -------------------------------
        # INVENTORY CHECK
        # -------------------------------

        print("\n── Inventory Check ──")

        inventory = await get(
            client,
            "/inventory",
            orion_id
        )

        for item in inventory:
            print(
                f"{item['sku']:20} | "
                f"on_hand={item['on_hand_quantity']} | "
                f"reserved={item['reserved_quantity']} | "
                f"available={item['available_quantity']}"
            )


        # -------------------------------
        # SALES ORDER
        # -------------------------------

        print("\n── Create Sales Order ──")

        sales_order_body = {
            "customer_id": orion_customer["id"],
            "warehouse_id": orion_main["id"],
            "order_number": "SO-2026-ORION-001",
            "items": [
                {
                    "sku": "FG-AWR-001",
                    "quantity": 3
                }
            ],
            "tax_percent": 18.0
        }

        sales_order = await post(
            client,
            "/sales-orders",
            sales_order_body,
            orion_id
        )

        so_id = sales_order["id"]

        print("Sales order created.")


        # -------------------------------
        # CONFIRM SALES ORDER
        # -------------------------------

        print("\n── Confirm Sales Order ──")

        confirmation = await post(
            client,
            f"/sales-orders/{so_id}/confirm",
            {},
            orion_id
        )

        print("Sales order confirmed.")
        print(confirmation)


        # -------------------------------
        # DISPATCH
        # -------------------------------

        print("\n── Dispatch Sales Order ──")

        dispatch_body = {
            "items": [
                {
                    "sku": "FG-AWR-001",
                    "quantity": 3
                }
            ]
        }

        dispatch = await post(
            client,
            f"/sales-orders/{so_id}/dispatch",
            dispatch_body,
            orion_id
        )

        print("Dispatch completed.")
        print(dispatch)


        # -------------------------------
        # STOCK LEDGER
        # -------------------------------

        print("\n── Stock Ledger ──")

        ledger = await get(
            client,
            "/stock-ledger",
            orion_id
        )

        print(f"Total Ledger Entries: {len(ledger)}")

        for entry in ledger[:10]:
            print(
                f"{entry['movement_type']:25} | "
                f"{entry['product_sku']:20} | "
                f"qty={entry['quantity_change']}"
            )


        # -------------------------------
        # FINAL SUCCESS
        # -------------------------------

        print("\n====================================")
        print("✓ SEED V2 COMPLETED SUCCESSFULLY")
        print("====================================")


if __name__ == "__main__":

    print("\nLaunching Seed V2...\n")

    try:
        asyncio.run(seed())

    except Exception as e:
        print(f"\n✗ SEED FAILED: {e}")
