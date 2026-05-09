from app.models.base import TenantScopedBase

class InventoryBalance(TenantScopedBase):
    warehouse_id: str
    product_id: str
    on_hand_quantity: float = 0.0
    reserved_quantity: float = 0.0
    average_cost: float = 0.0

    @property
    def available_quantity(self) -> float:
        return self.on_hand_quantity - self.reserved_quantity

    @property
    def inventory_value(self) -> float:
        return self.on_hand_quantity * self.average_cost
