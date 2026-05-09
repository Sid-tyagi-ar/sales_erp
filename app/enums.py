from enum import Enum

class ProductType(str, Enum):
    raw_material = "raw_material"
    finished_good = "finished_good"
    trading_good = "trading_good"

class MovementType(str, Enum):
    purchase_receipt = "purchase_receipt"
    sales_reservation = "sales_reservation"
    sales_dispatch = "sales_dispatch"
    reservation_release = "reservation_release"
    manufacturing_issue = "manufacturing_issue"
    manufacturing_receipt = "manufacturing_receipt"
    stock_adjustment = "stock_adjustment"

class OrderStatus(str, Enum):
    draft = "draft"
    confirmed = "confirmed"
    partially_dispatched = "partially_dispatched"
    dispatched = "dispatched"
    cancelled = "cancelled"

class ManufacturingStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"

class UnitOfMeasure(str, Enum):
    kg = "kg"
    unit = "unit"
    liter = "liter"
    meter = "meter"
    box = "box"
