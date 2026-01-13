import streamlit as st
import requests
import pandas as pd

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Cartons System", layout="wide")
st.title("📦 Carton Stock Management System")

# ---------------- HELPERS ----------------

def fetch_grades():
    try:
        res = requests.get(f"{API_URL}/grades")
        res.raise_for_status()
        return res.json()
    except:
        return []

def fetch_production_stock():
    try:
        res = requests.get(f"{API_URL}/production-stock")
        res.raise_for_status()
        return res.json()
    except:
        return []

def fetch_storage_stock():
    try:
        res = requests.get(f"{API_URL}/stock")
        res.raise_for_status()
        return res.json()
    except:
        return []

# ---------------- NAV ----------------

menu = st.sidebar.radio(
    "Navigation",
    ["Production", "Transfer", "Shipping", "Stock & Reports"],
    index=3  # <-- zero-based index, 3 = "Stock & Reports"
)


# Load grades once
grades = fetch_grades()
grade_map = {g["name"]: g["id"] for g in grades} if grades else {}

if not grades:
    st.warning("No grades found. Please add grades in the database first.")
    st.stop()

# ---------------- PRODUCTION ----------------
if menu == "Production":
    st.header("🏭 Record Production")

    production_date = st.date_input("Production Date")

    grade_name = st.selectbox("Grade", list(grade_map.keys()))
    grade_id = grade_map[grade_name]

    cartons = st.number_input("Cartons Produced", min_value=1, step=1)

    if st.button("Save Production"):
        payload = {
            "production_date": str(production_date),
            "grade_id": grade_id,
            "cartons": cartons
        }

        res = requests.post(f"{API_URL}/production", json=payload)

        if res.status_code == 200:
            st.success("Production recorded and added to Production Floor stock.")
        else:
            st.error(res.text)

# ---------------- TRANSFER ----------------
elif menu == "Transfer":
    st.header("🔄 Transfer Cartons (Production → Storage)")

    transfer_date = st.date_input("Transfer Date")

    grade_name = st.selectbox("Grade", list(grade_map.keys()))
    grade_id = grade_map[grade_name]

    cartons = st.number_input("Cartons to Transfer", min_value=1, step=1)

    if st.button("Transfer Stock"):
        payload = {
            "transfer_date": str(transfer_date),
            "grade_id": grade_id,
            "cartons": cartons
        }

        res = requests.post(f"{API_URL}/transfer", json=payload)

        if res.status_code == 200:
            st.success("Stock successfully transferred from Production to Storage.")
        else:
            st.error(res.text)

# ---------------- SHIPPING ----------------
elif menu == "Shipping":
    st.header("🚚 Record Shipment")

    shipment_date = st.date_input("Shipment Date")
    destination = st.text_input("Destination")

    st.subheader("Shipment Items")

    items = []
    count = st.number_input("Number of different grades", min_value=1, step=1)

    for i in range(int(count)):
        st.markdown(f"### Item {i+1}")

        grade_name = st.selectbox(
            f"Grade {i+1}", list(grade_map.keys()), key=f"g{i}"
        )
        grade_id = grade_map[grade_name]

        source = st.selectbox(
            f"Source {i+1}",
            ["PRODUCTION", "STORAGE"],
            key=f"s{i}"
        )

        cartons = st.number_input(
            f"Cartons {i+1}", min_value=1, step=1, key=f"c{i}"
        )

        items.append({
            "grade_id": grade_id,
            "source": source,
            "cartons": cartons
        })

    if st.button("Save Shipment"):
        payload = {
            "shipment_date": str(shipment_date),
            "destination": destination,
            "items": items
        }

        res = requests.post(f"{API_URL}/shipment", json=payload)

        if res.status_code == 200:
            st.success("Shipment recorded successfully and stock updated.")
        else:
            st.error(res.text)

# ---------------- STOCK & REPORTS ----------------
elif menu == "Stock & Reports":
    st.header("📊 Live Stock View")

    st.subheader("📦 Total Inventory (Production + Storage)")

    # Fetch production and storage stock
    prod = fetch_production_stock()
    store = fetch_storage_stock()

    if prod or store:
        # Create DataFrames or empty placeholders
        prod_df = pd.DataFrame(prod) if prod else pd.DataFrame(columns=["grade", "cartons"])
        store_df = pd.DataFrame(store) if store else pd.DataFrame(columns=["grade", "cartons"])

        # Rename columns for clarity
        prod_df = prod_df.rename(columns={"cartons": "production_cartons"})
        store_df = store_df.rename(columns={"cartons": "storage_cartons"})

        # Force integer type
        prod_df["production_cartons"] = prod_df["production_cartons"].astype(int)
        store_df["storage_cartons"] = store_df["storage_cartons"].astype(int)

        # Merge production and storage by grade
        merged = pd.merge(prod_df, store_df, on="grade", how="outer").fillna(0)

        # Calculate total cartons per grade
        merged["total_cartons"] = (merged["production_cartons"] + merged["storage_cartons"]).astype(int)

        # Add row for grand totals
        total_row = {
            "grade": "TOTAL",
            "production_cartons": merged["production_cartons"].sum(),
            "storage_cartons": merged["storage_cartons"].sum(),
            "total_cartons": merged["total_cartons"].sum()
        }
        merged = pd.concat([merged, pd.DataFrame([total_row])], ignore_index=True)

        # Display table
        st.table(merged)
    else:
        st.info("No inventory available.")
# ---------- Shipment Report ----------
    st.subheader("🚚 Shipment Report")

    try:
        res = requests.get(f"{API_URL}/shipments")
        shipments = res.json()
    except Exception as e:
        st.error(f"Could not fetch shipment data: {e}")
        shipments = []

    if shipments:
        # Flatten shipment items for display
        shipment_rows = []
        for s in shipments:
            for item in s.get("items", []):
                shipment_rows.append({
                    "date": s["shipment_date"],
                    "grade": item["grade_name"],
                    "source": item["source"],
                    "cartons": int(item["cartons"]),
                    "destination": s["destination"]
                })

        df_shipments = pd.DataFrame(shipment_rows)
        st.table(df_shipments)
    else:
        st.info("No shipments recorded yet.")