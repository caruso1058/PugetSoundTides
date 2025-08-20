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

with st.sidebar:
    station_name = st.selectbox("Station", list(STATIONS.keys()), index=0)
    station = STATIONS[station_name]
    product_label = st.selectbox("Data", list(PRODUCTS.keys()), index=0)
    product = PRODUCTS[product_label]
    days = st.slider("Days", min_value=1, max_value=7, value=2)
    fetch_now = st.button("Fetch / Refresh")

# ---- fetch data on demand ----
if fetch_now:
    # Compute date window
    start = dt.date.today()
    end = start + dt.timedelta(days=days - 1)

    # Observations cannot be in the future → clamp end to today
    if product == "water_level":
        today = dt.date.today()
        if end > today:
            end = today
        # If start accidentally goes past end (e.g., days=1 is fine), just enforce
        if start > end:
            start = end

    try:
        raw_path = fetch(
            station=station,
            start=start,
            end=end,
            out_dir=Path("data/raw"),
            product=product,
        )
        st.success(f"Fetched raw data → {raw_path.name}")
    except ValueError as e:
        # NOAA returned a structured error (e.g., no data for range)
        st.warning(str(e))
        st.stop()
    except Exception as e:
        st.error(f"Fetch failed: {e}")
        st.stop()

# ---- load latest raw for current selection and render ----
raw_dir = Path("data/raw")
raw_files = sorted(raw_dir.glob(f"{product}_{station}_*.json"))

if not raw_files:
    st.info("No raw data yet. Click **Fetch / Refresh** in the sidebar to pull NOAA data.")
else:
    try:
        df = tidy_from_raw(raw_files[-1], product=product)
    except Exception as e:
        st.error(f"Failed to parse raw file: {e}")
        st.stop()

    if df.empty:
        if product == "water_level":
            st.info("No observation rows returned for this window. Try fewer days or switch to Predictions.")
        else:
            st.info("No prediction rows returned. Try a different station or a shorter window.")
        st.stop()

    # UI
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
