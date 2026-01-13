from db import supabase

# ---------- PRODUCTION STOCK ----------
def get_production_stock(grade_id):
    res = supabase.table("production_stock").select("cartons").eq("grade_id", grade_id).execute()
    if not res.data:
        supabase.table("production_stock").insert({"grade_id": grade_id, "cartons": 0}).execute()
        return 0
    return int(res.data[0]["cartons"])  # <- ensure integer

def update_production_stock(grade_id, delta):
    current = get_production_stock(grade_id)
    new = int(current + delta)  # <- force integer
    if new < 0:
        raise ValueError("Not enough stock on production floor")
    supabase.table("production_stock").update({"cartons": new}).eq("grade_id", grade_id).execute()


# ---------- STORAGE STOCK ----------
def get_storage_stock(grade_id):
    res = supabase.table("stock").select("cartons").eq("grade_id", grade_id).execute()
    if not res.data:
        supabase.table("stock").insert({"grade_id": grade_id, "cartons": 0}).execute()
        return 0
    return int(res.data[0]["cartons"])  # <- ensure integer

def update_storage_stock(grade_id, delta):
    current = get_storage_stock(grade_id)
    new = int(current + delta)  # <- force integer
    if new < 0:
        raise ValueError("Not enough stock in storage")
    supabase.table("stock").update({"cartons": new}).eq("grade_id", grade_id).execute()



# ---------- RECORD PRODUCTION ----------
def record_production(data):
    supabase.table("production_log").insert({
        "production_date": str(data.production_date),  # <-- convert to string
        "grade_id": data.grade_id,
        "cartons_produced": data.cartons
    }).execute()

    update_production_stock(data.grade_id, data.cartons)


# ---------- TRANSFER (Production → Storage) ----------
def transfer_stock(data):
    update_production_stock(data.grade_id, -data.cartons)
    update_storage_stock(data.grade_id, data.cartons)

    supabase.table("transfers").insert({
        "transfer_date": str(data.transfer_date),  # <-- convert to string
        "grade_id": data.grade_id,
        "cartons": data.cartons
    }).execute()



# ---------- SHIPPING ----------
def record_shipment(data):
    shipment = supabase.table("shipments").insert({
        "shipment_date": str(data.shipment_date),
        "destination": data.destination
    }).execute().data[0]

    for item in data.items:
        if item.source == "PRODUCTION":
            update_production_stock(item.grade_id, -item.cartons)
        elif item.source == "STORAGE":
            update_storage_stock(item.grade_id, -item.cartons)
        else:
            raise ValueError("Invalid source: must be PRODUCTION or STORAGE")

        supabase.table("shipment_items").insert({
            "shipment_id": shipment["id"],
            "grade_id": item.grade_id,
            "source": item.source,
            "cartons": item.cartons
        }).execute()
