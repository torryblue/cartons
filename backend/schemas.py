from pydantic import BaseModel
from datetime import date
from typing import List

# ---------------- PRODUCTION ----------------
class ProductionIn(BaseModel):
    production_date: date
    grade_id: str
    cartons: int

# ---------------- TRANSFER ----------------
class TransferIn(BaseModel):
    transfer_date: date
    grade_id: str
    cartons: int

# ---------------- SHIPMENT ----------------
class ShipmentItem(BaseModel):
    grade_id: str
    source: str  # "PRODUCTION" or "STORAGE"
    cartons: int

class ShipmentIn(BaseModel):
    shipment_date: date
    destination: str
    items: List[ShipmentItem]
