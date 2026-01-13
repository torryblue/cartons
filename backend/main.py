from fastapi import FastAPI, HTTPException
from schemas import ProductionIn, TransferIn, ShipmentIn
from services import record_production, transfer_stock, record_shipment

from db import supabase

app = FastAPI()

# ---------------- PRODUCTION ----------------
@app.post("/production")
def create_production(data: ProductionIn):
    try:
        record_production(data)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---------------- TRANSFER ----------------
@app.post("/transfer")
def create_transfer(data: TransferIn):
    try:
        transfer_stock(data)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---------------- SHIPPING ----------------
@app.post("/shipment")
def create_shipment(data: ShipmentIn):
    try:
        record_shipment(data)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---------------- GRADES ----------------
@app.get("/grades")
def get_grades():
    res = supabase.table("grades").select("id, name").execute()
    return res.data

# ---------------- STOCK ENDPOINTS ----------------
@app.get("/production-stock")
def get_production_stock_endpoint():
    res = supabase.table("production_stock").select("grade_id, cartons, grades(name)").execute()
    data = [{"grade": row["grades"]["name"], "cartons": row["cartons"]} for row in res.data]
    return data

@app.get("/stock")
def get_storage_stock_endpoint():
    res = supabase.table("stock").select("grade_id, cartons, grades(name)").execute()
    data = [{"grade": row["grades"]["name"], "cartons": row["cartons"]} for row in res.data]
    return data
@app.get("/shipments")
def get_shipments():
    # Fetch shipments
    shipments = supabase.table("shipments").select("*").execute().data
    shipment_list = []

    for s in shipments:
        # Fetch items for each shipment
        items_res = supabase.table("shipment_items").select(
            "grade_id, cartons, source, grades(name)"
        ).eq("shipment_id", s["id"]).execute()
        items_data = []
        for i in items_res.data:
            items_data.append({
                "grade_id": i["grade_id"],
                "grade_name": i["grades"]["name"],
                "source": i["source"],
                "cartons": i["cartons"]
            })

        shipment_list.append({
            "shipment_date": s["shipment_date"],
            "destination": s["destination"],
            "items": items_data
        })

    return shipment_list
