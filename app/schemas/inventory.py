from pydantic import BaseModel

class InventoryBalanceResponse(BaseModel):
    product_id: str
    sku: str
    product_name: str
    warehouse_id: str
    warehouse_name: str
    on_hand_quantity: float
    reserved_quantity: float
    available_quantity: float
    average_cost: float
    inventory_value: float
