import httpx
import asyncio
import os
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

# Load environment variables from .env file
load_dotenv()

BASE_URL = "https://saleserp-production-e9b3.up.railway.app"

async def post(client: httpx.AsyncClient, path: str, body: Dict, tenant_id: Optional[str] = None) -> Dict:
  headers = {}
  if tenant_id:
    headers["X-Tenant-ID"] = tenant_id
  response = await client.post(
    f"{BASE_URL}{path}",
    json=body,
    headers=headers
  )
  if response.status_code not in [200, 201]:
    print(f"  ✗ FAILED POST {path}")
    print(f"    Status: {response.status_code}")
    print(f"    Body:   {response.text}")
    raise Exception(f"Step failed: POST {path}")
  data = response.json()
  print(f"  ✓ POST {path}")
  return data

async def get(client: httpx.AsyncClient, path: str, tenant_id: Optional[str] = None) -> Any:
  headers = {}
  if tenant_id:
    headers["X-Tenant-ID"] = tenant_id
  response = await client.get(
    f"{BASE_URL}{path}",
    headers=headers
  )
  if response.status_code != 200:
    print(f"  ✗ FAILED GET {path}")
    print(f"    Status: {response.status_code}")
    print(f"    Body:   {response.text}")
    raise Exception(f"GET failed: {path}")
  return response.json()

async def seed():
  # Fix 2: Set follow_redirects=True in httpx.AsyncClient
  async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:

    # Store customer IDs for later use
    alpha_customer_1_id: Optional[str] = None
    beta_customer_1_id: Optional[str] = None

    print("\n── Step 1: Health Check ──")
    health = await get(client, "/health")
    print(f"  Server status: {health['status']}")

    print("\n── Step 2: Create Tenants ──")
    
    tenant_alpha = await post(client, "/tenants", {
      "name": "Tenant Alpha",
      "email": "alpha@erp.com"
    })
    alpha_id = tenant_alpha["id"]
    print(f"    id: {alpha_id}")

    tenant_beta = await post(client, "/tenants", {
      "name": "Tenant Beta", 
      "email": "beta@erp.com"
    })
    beta_id = tenant_beta["id"]
    print(f"    id: {beta_id}")

    print("\n── Step 3: Create Warehouses ──")

    alpha_main_wh: Optional[str] = None
    alpha_sec_wh: Optional[str] = None
    beta_main_wh: Optional[str] = None
    beta_sec_wh: Optional[str] = None

    for tenant_id, label in [
      (alpha_id, "Alpha"), (beta_id, "Beta")
    ]:
      print(f"  Tenant {label}:")
      
      wh_main = await post(
        client, "/warehouses",
        {"name": "Main Warehouse", 
         "code": "MAIN", "city": "Mumbai"},
        tenant_id
      )
      print(f"    Main WH id: {wh_main['id']}")
      if tenant_id == alpha_id:
          alpha_main_wh = wh_main['id']
      else:
          beta_main_wh = wh_main['id']
      
      wh_sec = await post(
        client, "/warehouses",
        {"name": "Secondary Warehouse",
         "code": "SEC", "city": "Delhi"},
        tenant_id
      )
      print(f"    Sec  WH id: {wh_sec['id']}")
      if tenant_id == alpha_id:
          alpha_sec_wh = wh_sec['id']
      else:
          beta_sec_wh = wh_sec['id']

    print("\n── Step 4: Create Products ──")

    products_to_create = [
      {
        "name": "Steel Plate",
        "sku": "RM-STEEL-001",
        "type": "raw_material",
        "unit_of_measure": "kg",
        "standard_cost": 50.0,
        "selling_price": 0.0,
        "sellable": False
      },
      {
        "name": "Motor",
        "sku": "RM-MOTOR-001",
        "type": "raw_material",
        "unit_of_measure": "unit",
        "standard_cost": 200.0,
        "selling_price": 0.0,
        "sellable": False
      },
      {
        "name": "Control Panel",
        "sku": "RM-CP-001",
        "type": "raw_material",
        "unit_of_measure": "unit",
        "standard_cost": 150.0,
        "selling_price": 0.0,
        "sellable": False
      },
      {
        "name": "CNC Machine",
        "sku": "FG-CNC-001",
        "type": "finished_good",
        "unit_of_measure": "unit",
        "standard_cost": 1200.0,
        "selling_price": 1500.0,
        "sellable": True
      },
      {
        "name": "Hydraulic Press",
        "sku": "FG-HP-001",
        "type": "finished_good",
        "unit_of_measure": "unit",
        "standard_cost": 2000.0,
        "selling_price": 2500.0,
        "sellable": True
      },
      {
        "name": "Safety Kit",
        "sku": "TG-SK-001",
        "type": "trading_good",
        "unit_of_measure": "unit",
        "standard_cost": 30.0,
        "selling_price": 50.0,
        "sellable": True
      }
    ]

    for tenant_id, label in [
      (alpha_id, "Alpha"), (beta_id, "Beta")
    ]:
      print(f"  Tenant {label}:")
      for product in products_to_create:
        p = await post(
          client, "/products", 
          product, tenant_id)
        print(f"    {p['sku']}: {p['id']}")

    print("\n── Step 5: Create Customers ──")

    for tenant_id, label in [
      (alpha_id, "Alpha"), (beta_id, "Beta")
    ]:
      print(f"  Tenant {label}:")
      
      c1 = await post(
        client, "/customers",
        {
          "name": "Acme Corp",
          "email": f"acme@{label.lower()}.com",
          "phone": "9999999991",
          "address": "123 Industrial Area"
        },
        tenant_id
      )
      print(f"    Customer 1 id: {c1['id']}")
      if tenant_id == alpha_id:
          alpha_customer_1_id = c1["id"]
      else:
          beta_customer_1_id = c1["id"]

      c2 = await post(
        client, "/customers",
        {
          "name": "BuildRight Ltd",
          "email": f"buildright@{label.lower()}.com",
          "phone": "9999999992",
          "address": "456 Factory Road"
        },
        tenant_id
      )
      print(f"    Customer 2 id: {c2['id']}")

    print("\n── Step 6: Purchase Receipts ──")

    receipt_body_template = {
      "items": [
        {
          "sku": "RM-STEEL-001",
          "quantity": 100,
          "unit_cost": 50.0
        },
        {
          "sku": "RM-MOTOR-001",
          "quantity": 20,
          "unit_cost": 200.0
        },
        {
          "sku": "RM-CP-001",
          "quantity": 20,
          "unit_cost": 150.0
        }
      ]
    }

    for tenant_id, wh_id, label in [
      (alpha_id, alpha_main_wh, "Alpha"),
      (beta_id,  beta_main_wh,  "Beta")
    ]:
      print(f"  Tenant {label}:")
      body = {**receipt_body_template, "warehouse_id": wh_id}
      receipt = await post(
        client, "/purchase-receipts",
        body, tenant_id)
      print(f"    Receipt id: {receipt['id']}")
      print(f"    Ledger entries: "
            f"{receipt['ledger_entry_ids']}")

    print("\n── Step 7: Verify Inventory After Receipt ──")

    for tenant_id, label in [
      (alpha_id, "Alpha"), (beta_id, "Beta")
    ]:
      print(f"  Tenant {label}:")
      inventory = await get(
        client, "/inventory", tenant_id)
      for item in inventory:
        # Only print relevant items for brevity
        if item['sku'] in ["RM-STEEL-001", "RM-MOTOR-001", "RM-CP-001"]:
            print(
            f"    {item['sku']:20} | "
            f"on_hand: {item['on_hand_quantity']:6} | "
            f"available: {item['available_quantity']:6} | "
            f"avg_cost: {item['average_cost']:8.2f}"
            )

    print("\n── Step 8: Define BOM ──")

    bom_body = {
      "finished_good_sku": "FG-CNC-001",
      "components": [
        {
          "raw_material_sku": "RM-STEEL-001",
          "quantity_required": 5.0,
          "wastage_percent": 2.0
        },
        {
          "raw_material_sku": "RM-MOTOR-001",
          "quantity_required": 1.0,
          "wastage_percent": 0.0
        },
        {
          "raw_material_sku": "RM-CP-001",
          "quantity_required": 1.0,
          "wastage_percent": 0.0
        }
      ]
    }

    for tenant_id, label in [
      (alpha_id, "Alpha"), (beta_id, "Beta")
    ]:
      print(f"  Tenant {label}:")
      bom = await post(
        client, "/bom", bom_body, tenant_id)
      print(f"    BOM for: {bom['finished_good_sku']}")
      for comp in bom["components"]:
        print(
          f"      {comp['raw_material_sku']:20} | "
          f"required: {comp['quantity_required']} | "
          f"effective: {comp['effective_quantity']:.3f}"
        )

    print("\n── Step 9: Manufacture 10 CNC Machines ──")

    mfg_body_template = {
      "finished_good_sku": "FG-CNC-001",
      "quantity_to_produce": 10
    }

    for tenant_id, wh_id, label in [
      (alpha_id, alpha_main_wh, "Alpha"),
      (beta_id,  beta_main_wh,  "Beta")
    ]:
      print(f"  Tenant {label}:")
      body = {**mfg_body_template, "warehouse_id": wh_id}
      
      order = await post(
        client, "/manufacturing-orders",
        body, tenant_id)
      order_id = order["id"]
      print(f"    Order created: {order_id}")

      result = await post(
        client,
        f"/manufacturing-orders/{order_id}/complete",
        {},
        tenant_id
      )
      
      if result["can_complete"]:
        print(f"    ✓ Completed successfully")
        print(f"    Actual cost: {result['actual_cost']}")
        print(f"    Ledger entries: "
              f"{len(result['ledger_entry_ids'])}")
      else:
        print(f"    ✗ Cannot complete — shortages:")
        for s in result["shortages"]:
          print(
            f"      {s['sku']}: "
            f"need {s['required']} "
            f"have {s['available']} "
            f"short {s['shortage']}"
          )

    print("\n── Step 10: Verify Inventory After Manufacture ──")

    for tenant_id, label in [
      (alpha_id, "Alpha"), (beta_id, "Beta")
    ]:
      print(f"  Tenant {label}:")
      inventory = await get(
        client, "/inventory", tenant_id)
      for item in inventory:
        if item['sku'] in ["RM-STEEL-001", "RM-MOTOR-001", "RM-CP-001", "FG-CNC-001"]:
            print(
            f"    {item['sku']:20} | "
            f"on_hand: {item['on_hand_quantity']:6} | "
            f"reserved: {item['reserved_quantity']:6} | "
            f"available: {item['available_quantity']:6}"
            )

    print("\n── Step 11: Create Sales Order (8 CNC) ──")

    # Ensure alpha_customer_1_id is set from step 5
    if alpha_customer_1_id is None:
        raise Exception("alpha_customer_1_id not set. Seed script logic error.")

    order_body = {
      "customer_id": alpha_customer_1_id,
      "warehouse_id": alpha_main_wh,
      "order_number": "SO-2024-001",
      "items": [
        {
          "sku": "FG-CNC-001",
          "quantity": 8
        }
      ],
      "tax_percent": 18.0
    }

    so = await post(
      client, "/sales-orders",
      order_body, alpha_id)
    so_id = so["id"]
    print(f"  Order id:      {so_id}")
    print(f"  Status:        {so['status']}")
    print(f"  Subtotal:      {so['subtotal']}")
    print(f"  Tax:           {so['tax']}")
    print(f"  Grand Total:   {so['grand_total']}")

    print("\n── Step 12: Confirm Sales Order ──")

    confirmed = await post(
      client,
      f"/sales-orders/{so_id}/confirm",
      {},
      alpha_id
    )
    print(f"  Status: {confirmed['status']}")

    print("Verify inventory shows reserved:")
    inventory = await get(
      client, "/inventory", alpha_id)
    for item in inventory:
      if item["sku"] == "FG-CNC-001":
        print(f"  CNC Machine inventory:")
        print(f"    on_hand:   {item['on_hand_quantity']}")
        print(f"    reserved:  {item['reserved_quantity']}")
        print(f"    available: {item['available_quantity']}")

    print("\n── Step 13: Test Insufficient Stock ──")

    order2_body = {
      "customer_id": alpha_customer_1_id,
      "warehouse_id": alpha_main_wh,
      "order_number": "SO-2024-002",
      "items": [{"sku": "FG-CNC-001", "quantity": 5}],
      "tax_percent": 18.0
    }

    so2 = await post(
      client, "/sales-orders",
      order2_body, alpha_id)
    so2_id = so2["id"]

    print("Try to confirm — this should fail with shortage:")
    headers = {"X-Tenant-ID": alpha_id}
    response = await client.post(
      f"{BASE_URL}/sales-orders/{so2_id}/confirm",
      json={},
      headers=headers
    )
    
    if response.status_code == 400:
      body = response.json()
      # handle both flat and nested detail shapes
      error_data = body.get("detail", body)
      if isinstance(error_data, str):
        print(f"  ✓ Correctly rejected: {error_data}")
      else:
        print(f"  ✓ Correctly rejected with: "
              f"{error_data.get('error', 'UNKNOWN')}")
        print(f"  Message: "
              f"{error_data.get('message', '')}")
        details = error_data.get("details", [])
        if details:
          print(f"  Shortage details:")
          for d in details:
            print(f"    {d}")
    elif response.status_code == 200:
      print(f"  ✗ Should have been rejected but wasn't!")
    else:
      print(f"  ✗ Unexpected status: "
            f"{response.status_code}")
      print(f"    {response.text}")

    print("\n── Step 14: Dispatch Order ──")

    dispatch_body = {
      "items": [
        {"sku": "FG-CNC-001", "quantity": 8}
      ]
    }

    dispatched = await post(
      client,
      f"/sales-orders/{so_id}/dispatch",
      dispatch_body,
      alpha_id
    )
    print(f"  Status: {dispatched['status']}")

    print("Final inventory check:")
    inventory = await get(
      client, "/inventory", alpha_id)
    for item in inventory:
      if item["sku"] == "FG-CNC-001":
        print(f"  CNC Machine final inventory:")
        print(f"    on_hand:   {item['on_hand_quantity']}")
        print(f"    reserved:  {item['reserved_quantity']}")
        print(f"    available: {item['available_quantity']}")

    print("\n── Step 15: Stock Ledger ──")

    ledger = await get(
      client, "/stock-ledger", alpha_id)
    print(f"  Total entries: {len(ledger)}")
    for entry in ledger[:10]:
      print(
        f"    {entry['movement_type']:25} | "
        f"{entry['product_sku']:20} | "
        f"qty: {entry['quantity_change']:8} | "
        f"ref: {entry['reference_type']}"
      )

    print("\n── Step 16: Audit Log ──")

    audit = await get(
      client, "/audit-log", alpha_id)
    print(f"  Total audit entries: {len(audit)}")
    for entry in audit[:10]:
      print(
        f"    {entry['event_type']:30} | "
        f"{entry['entity_type']:20} | "
        f"{entry['description']}"
      )

    print("\n" + "="*50)
    print("✓ SEED COMPLETED SUCCESSFULLY")
    print("="*50)


if __name__ == "__main__":
  import asyncio
  print("Starting seed...")
  print("Make sure server is running on localhost:8000")
  try:
    asyncio.run(seed())
  except Exception as e:
    print(f"\n✗ SEED FAILED: {e}")
    exit(1)