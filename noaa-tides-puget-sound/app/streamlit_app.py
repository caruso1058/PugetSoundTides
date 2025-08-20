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
PRODUCTS = {"Predictions (forecast)": "predictions", "Observations (water_level)": "water_level"}

st.set_page_config(page_title="Puget Sound Tides", page_icon="🌊", layout="wide")
st.title("🌊 Puget Sound Tides — NOAA (Predictions & Observations)")

with st.sidebar:
    station_name = st.selectbox("Station", list(STATIONS.keys()), index=0)
    station = STATIONS[station_name]
    product_label = st.selectbox("Data", list(PRODUCTS.keys()), index=0)
    product = PRODUCTS[product_label]
    days = st.slider("Days", min_value=1, max_value=7, value=2)
    fetch_now = st.button("Fetch / Refresh")

if fetch_now:
    start = dt.date.today(); end = start + dt.timedelta(days=days - 1)
    raw_path = fetch(station=station, start=start, end=end, out_dir=Path("data/raw"), product=product)
    st.success(f"Fetched raw data → {raw_path.name}")

raw_dir = Path("data/raw")
raw_files = sorted(raw_dir.glob(f"{product}_{station}_*.json"))
if not raw_files:
    st.info("No raw data yet. Click **Fetch / Refresh**.")
else:
    df = tidy_from_raw(raw_files[-1], product=product)
    if df.empty:
        st.warning("No rows in latest raw file.")
    else:
        st.subheader(f"{station_name} — {product_label} — Next {days} day(s)")
        st.line_chart(df.set_index("timestamp")["tide_ft"])
        with st.expander("Preview data (head)"):
            st.dataframe(df.head(100))
        st.download_button(
            "Download CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"tides_{product}_{station}.csv",
            mime="text/csv",
        )
