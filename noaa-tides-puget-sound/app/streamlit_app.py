# --- path shim so imports work on Streamlit Cloud ---
import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
# --- end shim ---

import datetime as dt
from pathlib import Path

import streamlit as st

from src.noaa_tides_ps.fetch import fetch
from src.noaa_tides_ps.transform import tidy_from_raw

STATIONS = {
    "Seattle (9447130)": "9447130",
    "Tacoma (9446484)": "9446484",
    "Port Townsend (9444900)": "9444900",
    "Everett (9447659)": "9447659",
}

PRODUCTS = {
    "Predictions (forecast)": "predictions",
    "Observations (water_level)": "water_level",
}

st.set_page_config(page_title="Puget Sound Tides", page_icon="🌊", layout="wide")
st.title("🌊 Puget Sound Tides — NOAA (Predictions & Observations)")

# --- UI controls ---
with st.sidebar:
    station_name = st.selectbox("Station", list(STATIONS.keys()), index=0, key="station_sel")
    station = STATIONS[station_name]

    product_label = st.selectbox("Data", list(PRODUCTS.keys()), index=0, key="product_sel")
    product = PRODUCTS[product_label]

    if product == "predictions":
        days = st.slider("Days ahead", min_value=1, max_value=7, value=2, key="days_ahead")
    else:
        days = st.slider("Days back", min_value=1, max_value=7, value=2, key="days_back")

    auto_fetch = st.checkbox("Auto-fetch on change", value=True)
    fetch_now = st.button("Fetch / Refresh now")

# --- remember the last selection to auto-fetch on changes ---
if "last_sel" not in st.session_state:
    st.session_state.last_sel = {"station": None, "product": None, "days": None}

selection = {"station": station, "product": product, "days": days}
selection_changed = selection != st.session_state.last_sel

def compute_window(product: str, days: int) -> tuple[dt.date, dt.date]:
    today = dt.date.today()
    if product == "predictions":
        start = today
        end = today + dt.timedelta(days=days - 1)  # forward window
    else:
        end = today
        start = end - dt.timedelta(days=days - 1)  # backward window
    return start, end

def do_fetch():
    start, end = compute_window(product, days)
    try:
        raw_path = fetch(
            station=station,
            start=start,
            end=end,
            out_dir=Path("data/raw"),
            product=product,
        )
        st.success(f"Fetched raw data → {raw_path.name}")
        st.session_state.last_sel = selection
    except ValueError as e:
        st.warning(str(e))
        st.stop()
    except Exception as e:
        st.error(f"Fetch failed: {e}")
        st.stop()

# --- fetch when needed ---
if fetch_now or (auto_fetch and selection_changed):
    do_fetch()

# --- load the most recent raw file for this selection ---
raw_dir = Path("data/raw")
raw_files = sorted(raw_dir.glob(f"{product}_{station}_*.json"))

if not raw_files:
    st.info("No raw data yet. Click **Fetch / Refresh now** in the sidebar.")
    st.stop()

# latest for current selection
raw_path = raw_files[-1]

# parse + render
try:
    df = tidy_from_raw(raw_path, product=product)
except Exception as e:
    st.error(f"Failed to parse raw file: {e}")
    st.stop()

if df.empty:
    msg = "No rows returned."
    if product == "water_level":
        msg += " Try fewer days back or switch to Predictions."
    st.info(msg)
    st.stop()

st.subheader(f"{station_name} — {product_label}")
st.line_chart(df.set_index("timestamp")["tide_ft"])

with st.expander("Preview data (first 100 rows)"):
    st.dataframe(df.head(100))

st.download_button(
    "Download CSV",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name=f"tides_{product}_{station}.csv",
    mime="text/csv",
)
