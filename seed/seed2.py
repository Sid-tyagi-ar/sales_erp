import asyncio
import uuid
import httpx

BASE_URL = "https://saleserp-production-e9b3.up.railway.app"

RUN_ID = str(uuid.uuid4())[:8]
RUN_ID_UPPER = RUN_ID.upper()

ALPHA_NAME = f"Orion Forge {RUN_ID_UPPER}"
BETA_NAME = f"Nebula Works {RUN_ID_UPPER}"

ALPHA_EMAIL = f"orion_{RUN_ID}@erp.com"
BETA_EMAIL = f"nebula_{RUN_ID}@erp.com"

SO_NUMBER = f"SO-{RUN_ID_UPPER}"

RM_TI_SKU = f"RM-TI-{RUN_ID_UPPER}"
RM_SERVO_SKU = f"RM-SERVO-{RUN_ID_UPPER}"
RM_SENSOR_SKU = f"RM-SENSOR-{RUN_ID_UPPER}"
FG_SKU = f"FG-AWR-{RUN_ID_UPPER}"

print("\n====================================")
print(" SALES ERP LIVE VALIDATION SEED ")
print("====================================\n")


async def post(client, path, body, tenant_id=None):
    headers = {}

    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id

    r = await client.post(
        f"{BASE_URL}{path}",
        json=body,
        headers=headers
    )

    print(f"POST {path} -> {r.status_code}")

    if r.status_code not in [200, 201]:
        print(r.text)
        raise Exception(f"POST failed: {path}")

    return r.json()


async def get(client, path, tenant_id=None):
    headers = {}

    if tenant_id:
        headers["X-Tenant-ID"] = tenant_id

    r = await client.get(
        f"{BASE_URL}{path}",
        headers=headers
    )

    print(f"GET {path} -> {r.status_code}")

    if r.status_code != 200:
        print(r.text)
        raise Exception(f"GET failed: {path}")

    return r.json()


async def main():
    async with httpx.AsyncClient(timeout=60) as client:

        print("\n── Health Check ──")

        health = await get(client, "/health")
        print("Server:", health)

        print("\n── Create Tenants ──")

        alpha = await post(
            client,
            "/tenants",
            {
                "name": ALPHA_NAME,
                "email": ALPHA_EMAIL
            }
        )

        beta = await post(
            client,
            "/tenants",
            {
                "name": BETA_NAME,
                "email": BETA_EMAIL
            }
        )

        alpha_tenant = alpha["id"]
        beta_tenant = beta["id"]

        print("Alpha Tenant:", alpha_tenant)
        print("Beta Tenant :", beta_tenant)

        print("\n── Create Warehouses ──")

        alpha_wh = await post(
            client,
            "/warehouses",
            {
                "name": "Orion Central Warehouse",
                "code": f"ORION-{RUN_ID_UPPER}",
                "city": "Bangalore"
            },
            alpha_tenant
        )

        await post(
            client,
            "/warehouses",
            {
                "name": "Nebula Operations Hub",
                "code": f"NEBULA-{RUN_ID_UPPER}",
                "city": "Pune"
            },
            beta_tenant
        )

        alpha_wh_id = alpha_wh["id"]

        print("\n── Create Products ──")

        products = [
            {
                "name": "Titanium Sheet",
                "sku": RM_TI_SKU,
                "type": "raw_material",
                "unit_of_measure": "kg",
                "standard_cost": 120,
                "selling_price": 0,
                "sellable": False
            },
            {
                "name": "Servo Motor",
                "sku": RM_SERVO_SKU,
                "type": "raw_material",
                "unit_of_measure": "unit",
                "standard_cost": 500,
                "selling_price": 0,
                "sellable": False
            },
            {
                "name": "Precision Sensor",
                "sku": RM_SENSOR_SKU,
                "type": "raw_material",
                "unit_of_measure": "unit",
                "standard_cost": 250,
                "selling_price": 0,
                "sellable": False
            },
            {
                "name": "Autonomous Welding Robot",
                "sku": FG_SKU,
                "type": "finished_good",
                "unit_of_measure": "unit",
                "standard_cost": 12000,
                "selling_price": 18000,
                "sellable": True
            }
        ]

        for p in products:
            await post(client, "/products", p, alpha_tenant)

        print("\n── Create Customer ──")

        customer = await post(
            client,
            "/customers",
            {
                "name": "Apex Robotics",
                "email": f"orders_{RUN_ID}@apexrobotics.com",
                "phone": "9999999999",
                "address": "Mumbai"
            },
            alpha_tenant
        )

        print("\n── Purchase Receipt ──")

        await post(
            client,
            "/purchase-receipts",
            {
                "warehouse_id": alpha_wh_id,
                "items": [
                    {
                        "sku": RM_TI_SKU,
                        "quantity": 200,
                        "unit_cost": 120
                    },
                    {
                        "sku": RM_SERVO_SKU,
                        "quantity": 30,
                        "unit_cost": 500
                    },
                    {
                        "sku": RM_SENSOR_SKU,
                        "quantity": 50,
                        "unit_cost": 250
                    }
                ]
            },
            alpha_tenant
        )

        print("\n── Create BOM ──")

        await post(
            client,
            "/bom",
            {
                "finished_good_sku": FG_SKU,
                "components": [
                    {
                        "raw_material_sku": RM_TI_SKU,
                        "quantity_required": 8,
                        "wastage_percent": 1.5
                    },
                    {
                        "raw_material_sku": RM_SERVO_SKU,
                        "quantity_required": 2,
                        "wastage_percent": 0
                    },
                    {
                        "raw_material_sku": RM_SENSOR_SKU,
                        "quantity_required": 4,
                        "wastage_percent": 0
                    }
                ]
            },
            alpha_tenant
        )

        print("\n── Manufacturing Order ──")

        mfg = await post(
            client,
            "/manufacturing-orders",
            {
                "warehouse_id": alpha_wh_id,
                "finished_good_sku": FG_SKU,
                "quantity_to_produce": 5
            },
            alpha_tenant
        )

        await post(
            client,
            f"/manufacturing-orders/{mfg['id']}/complete",
            {},
            alpha_tenant
        )

        print("\n── Verify Inventory ──")

        inventory = await get(
            client,
            "/inventory",
            alpha_tenant
        )

        for item in inventory:
            print(
                f"{item['sku']:25} | "
                f"on_hand={item['on_hand_quantity']} | "
                f"reserved={item['reserved_quantity']} | "
                f"available={item['available_quantity']}"
            )

        print("\n── Create Sales Order ──")

        so = await post(
            client,
            "/sales-orders",
            {
                "customer_id": customer["id"],
                "warehouse_id": alpha_wh_id,
                "order_number": SO_NUMBER,
                "items": [
                    {
                        "sku": FG_SKU,
                        "quantity": 3
                    }
                ],
                "tax_percent": 18
            },
            alpha_tenant
        )

        print("\n── Confirm Sales Order ──")

        confirm = await post(
            client,
            f"/sales-orders/{so['id']}/confirm",
            {},
            alpha_tenant
        )

        print(confirm)

        print("\n── Dispatch Sales Order ──")

        dispatch = await post(
            client,
            f"/sales-orders/{so['id']}/dispatch",
            {
                "items": [
                    {
                        "sku": FG_SKU,
                        "quantity": 3
                    }
                ]
            },
            alpha_tenant
        )

        print(dispatch)

        print("\n── Stock Ledger ──")

        ledger = await get(
            client,
            "/stock-ledger",
            alpha_tenant
        )

        print("Total Ledger Entries:", len(ledger))

        for entry in ledger[:10]:
            print(
                f"{entry['movement_type']:28} | "
                f"{entry['product_sku']:25} | "
                f"qty={entry['quantity_change']}"
            )

        print("\n====================================")
        print(" LIVE ERP FLOW VERIFIED SUCCESSFULLY ")
        print("====================================\n")


asyncio.run(main())