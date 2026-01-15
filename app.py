import streamlit as st
import pandas as pd
from datetime import date
from supabase import create_client, Client

# ---------------- SUPABASE CLIENT ----------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="📦 Cartons Live", layout="wide")
st.title("📦 Carton Stock Management System")

# ---------------- SIDEBAR ----------------
menu = st.sidebar.radio(
    "Navigation",
    ["Production", "Transfer", "Shipping", "Stock & Reports"],
    index=3  # make Stock & Reports landing page
)

# ---------------- HELPER FUNCTIONS ----------------
@st.cache_data
def fetch_grades():
    res = supabase.table("grades").select("id, name").execute()
    return res.data or []

@st.cache_data
def fetch_locations():
    res = supabase.table("locations").select("id, name").execute()
    return res.data or []

def fetch_production_stock():
    res = supabase.table("production_stock").select("grade_id, cartons, grades(name)").execute()
    data = res.data or []
    return [{"grade": d["grades"]["name"], "cartons": int(d["cartons"])} for d in data]

def fetch_storage_stock():
    res = supabase.table("stock").select("grade_id, cartons, grades(name)").execute()
    data = res.data or []
    return [{"grade": d["grades"]["name"], "cartons": int(d["cartons"])} for d in data]

def fetch_shipments():
    all_items = []
    res = supabase.table("shipments").select("id, shipment_date, destination").execute()
    shipments = res.data or []

    for s in shipments:
        items_res = supabase.table("shipment_items") \
            .select("grade_id, cartons, location") \
            .eq("shipment_id", s["id"]).execute()

        for item in items_res.data or []:
            all_items.append({
                "Date": s["shipment_date"],
                "Grade": grade_map.get(item["grade_id"], "Unknown"),  # UUID -> actual grade name
                "Cartons": int(item["cartons"]),
                "From": item["location"],
                "To": s["destination"]
            })
    return all_items

# ---------------- FETCH GRADES & LOCATIONS ----------------
grades = fetch_grades()
locations = fetch_locations()
# Correct mapping: UUID -> grade name
grade_map = {g["id"]: g["name"] for g in grades}
# Simple mapping for locations (optional, could extend for IDs if needed)
location_map = {l["id"]: l["name"] for l in locations}

# ---------------- PRODUCTION ----------------
if menu == "Production":
    st.header("🏭 Record Production")
    production_date = st.date_input("Production Date", date.today())
    grade_name = st.selectbox("Grade", list(grade_map.values()))
    cartons = st.number_input("Cartons Produced", min_value=1, step=1)

    if st.button("Record Production"):
        # Map grade name back to UUID
        grade_id = next((g["id"] for g in grades if g["name"] == grade_name), None)
        if not grade_id:
            st.error("Selected grade not found.")
        else:
            payload = {
                "production_date": str(production_date),
                "grade_id": grade_id,
                "cartons": cartons
            }
            supabase.table("production").insert(payload).execute()
            # Update production_stock
            stock = supabase.table("production_stock").select("cartons").eq("grade_id", grade_id).single().execute()
            if not stock.data:
                supabase.table("production_stock").insert({"grade_id": grade_id, "cartons": cartons}).execute()
            else:
                new_stock = int(stock.data["cartons"]) + cartons
                supabase.table("production_stock").update({"cartons": new_stock}).eq("grade_id", grade_id).execute()
            st.success("Production recorded and stock updated!")

# ---------------- TRANSFER ----------------
elif menu == "Transfer":
    st.header("🔄 Transfer Cartons (Production → Storage)")
    grade_name = st.selectbox("Grade", list(grade_map.values()))
    from_location_name = "Production Floor"
    to_location_name = "Storage"
    cartons = st.number_input("Cartons to Transfer", min_value=1, step=1)

    if st.button("Transfer Stock"):
        grade_id = next((g["id"] for g in grades if g["name"] == grade_name), None)
        if not grade_id:
            st.error("Selected grade not found.")
        else:
            # Subtract from production
            stock = supabase.table("production_stock").select("cartons").eq("grade_id", grade_id).single().execute()
            current_prod = int(stock.data["cartons"]) if stock.data else 0
            if cartons > current_prod:
                st.error(f"Not enough stock on production floor (available: {current_prod})")
            else:
                supabase.table("production_stock").update({"cartons": current_prod - cartons}).eq("grade_id", grade_id).execute()
                # Add to storage
                storage = supabase.table("stock").select("cartons").eq("grade_id", grade_id).single().execute()
                current_store = int(storage.data["cartons"]) if storage.data else 0
                if storage.data:
                    supabase.table("stock").update({"cartons": current_store + cartons}).eq("grade_id", grade_id).execute()
                else:
                    supabase.table("stock").insert({"grade_id": grade_id, "cartons": cartons}).execute()
                st.success(f"{cartons} cartons transferred to Storage!")

# ---------------- SHIPPING ----------------
elif menu == "Shipping":
    st.header("🚚 Record Shipment")
    shipment_date = st.date_input("Shipment Date", date.today())
    destination = st.text_input("Destination")

    st.subheader("Shipment Items")
    items = []
    count = st.number_input("Number of items", min_value=1, step=1)

    for i in range(count):
        st.markdown(f"**Item {i+1}**")
        grade_name = st.selectbox(f"Grade {i+1}", list(grade_map.values()), key=f"g{i}")
        location_name = st.selectbox(f"From Location {i+1}", ["Production Floor", "Storage"], key=f"l{i}")
        cartons = st.number_input(f"Cartons {i+1}", min_value=1, step=1)
        grade_id = next((g["id"] for g in grades if g["name"] == grade_name), None)
        items.append({
            "grade_id": grade_id,
            "location": location_name,
            "cartons": cartons
        })

    if st.button("Record Shipment"):
        shipment = supabase.table("shipments").insert({
            "shipment_date": str(shipment_date),
            "destination": destination
        }).execute()
        shipment_id = shipment.data[0]["id"]
        for item in items:
            # Deduct stock
            stock_table = "production_stock" if item["location"] == "Production Floor" else "stock"
            stock = supabase.table(stock_table).select("cartons").eq("grade_id", item["grade_id"]).single().execute()
            current = int(stock.data["cartons"]) if stock.data else 0
            if item["cartons"] > current:
                st.error(f"Not enough stock in {item['location']} for {grade_map.get(item['grade_id'], 'Unknown')}")
                continue
            supabase.table(stock_table).update({"cartons": current - item["cartons"]}).eq("grade_id", item["grade_id"]).execute()
            # Record shipment item
            supabase.table("shipment_items").insert({
                "shipment_id": shipment_id,
                "grade_id": item["grade_id"],
                "location": item["location"],
                "cartons": item["cartons"]
            }).execute()
        st.success("Shipment recorded!")

# ---------------- STOCK & REPORTS ----------------
elif menu == "Stock & Reports":
    st.header("📊 Live Stock & Reports")

    # ---------- TOTAL STOCK ----------
    prod = fetch_production_stock()
    store = fetch_storage_stock()

    prod_df = pd.DataFrame(prod) if prod else pd.DataFrame(columns=["grade", "cartons"])
    store_df = pd.DataFrame(store) if store else pd.DataFrame(columns=["grade", "cartons"])

    prod_df = prod_df.rename(columns={"cartons": "production_cartons"})
    store_df = store_df.rename(columns={"cartons": "storage_cartons"})

    merged = pd.merge(prod_df, store_df, on="grade", how="outer").fillna(0)
    merged["production_cartons"] = merged["production_cartons"].astype(int)
    merged["storage_cartons"] = merged["storage_cartons"].astype(int)
    merged["total_cartons"] = merged["production_cartons"] + merged["storage_cartons"]

    # Add totals row
    totals = pd.DataFrame([{
        "grade": "TOTAL",
        "production_cartons": merged["production_cartons"].sum(),
        "storage_cartons": merged["storage_cartons"].sum(),
        "total_cartons": merged["total_cartons"].sum()
    }])
    merged_display = pd.concat([merged, totals], ignore_index=True)

    st.subheader("📦 Current Inventory")
    st.table(merged_display)

    # ---------- SHIPMENT REPORT ----------
    st.subheader("🚛 Shipment History")
    shipment_data = fetch_shipments()
    if shipment_data:
        df_ship = pd.DataFrame(shipment_data)
        # Add totals row for cartons
        totals_row = pd.DataFrame([{
            "Date": "TOTAL",
            "Grade": "",
            "Cartons": df_ship["Cartons"].sum(),
            "From": "",
            "To": ""
        }])
        df_ship_display = pd.concat([df_ship, totals_row], ignore_index=True)
        st.table(df_ship_display)
    else:
        st.info("No shipments recorded yet.")
