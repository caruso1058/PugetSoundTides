# --- path shim so imports work on Streamlit Cloud ---
import sys, os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
# --- end shim ---

import datetime as dt
from pathlib import Path

import streamlit as st
import pandas as pd

try:
    import matplotlib.pyplot as plt
    from matplotlib.dates import AutoDateLocator, DateFormatter
    MATPLOTLIB_AVAILABLE = True
    MATPLOTLIB_IMPORT_ERROR = ""
except Exception as exc:
    MATPLOTLIB_AVAILABLE = False
    MATPLOTLIB_IMPORT_ERROR = str(exc)

from src.noaa_tides_ps.fetch import fetch
from src.noaa_tides_ps.transform import tidy_from_raw

STATIONS = {
    "Seattle (9447130)": "9447130",
    "Tacoma (9446484)": "9446484",
    "Port Townsend (9444900)": "9444900",
    "Everett (9447659)": "9447659",
    "Neah Bay (9443090)": "9443090",
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
        st.session_state.current_raw_path = str(raw_path)
        st.session_state.last_sel = selection
    except ValueError as e:
        st.warning(str(e))
        st.stop()
    except Exception as e:
        st.error(f"Fetch failed: {e}")
        st.stop()


def render_tide_chart(df):
    if not MATPLOTLIB_AVAILABLE:
        st.warning("Matplotlib unavailable; showing basic line chart.")
        if MATPLOTLIB_IMPORT_ERROR:
            st.caption(f"Matplotlib import error: {MATPLOTLIB_IMPORT_ERROR}")
        st.line_chart(df.set_index("timestamp")["tide_ft"])
        return

    fig, ax = plt.subplots(figsize=(10, 4))
    line_color = "#2c7fb8"
    ax.plot(df["timestamp"], df["tide_ft"], linewidth=2.3, color=line_color)
    ax.set_xlabel("Time")
    ax.set_ylabel("Tide (ft)")
    ax.set_title("Tide Levels with Sunrise/Sunset")

    locator = AutoDateLocator(minticks=4, maxticks=10)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(DateFormatter("%b %d\n%I:%M %p"))

    y_min, y_max = float(df["tide_ft"].min()), float(df["tide_ft"].max())
    pad = max(0.3, (y_max - y_min) * 0.10)
    chart_floor = -2.0
    ax.set_ylim(chart_floor, y_max + pad)
    ax.fill_between(df["timestamp"], df["tide_ft"], chart_floor, color=line_color, alpha=0.18)
    ax.yaxis.grid(True, linestyle="--", linewidth=0.8, alpha=0.45)
    ax.xaxis.grid(False)

    if "sunrise" in df.columns:
        for ts in sorted(pd.to_datetime(df["sunrise"], errors="coerce").dropna().unique()):
            ts = pd.Timestamp(ts)
            ax.axvline(ts, color="#d4a017", linestyle="--", linewidth=1.1, alpha=0.8)
            label = ts.strftime("Sunrise %I:%M %p").replace(" 0", " ")
            ax.annotate(label, (ts, y_max + pad * 0.95), rotation=90, ha="right", va="top", fontsize=8, color="#8a6a00")

    if "sunset" in df.columns:
        for ts in sorted(pd.to_datetime(df["sunset"], errors="coerce").dropna().unique()):
            ts = pd.Timestamp(ts)
            ax.axvline(ts, color="#2f5aa8", linestyle="--", linewidth=1.1, alpha=0.8)
            label = ts.strftime("Sunset %I:%M %p").replace(" 0", " ")
            ax.annotate(label, (ts, y_max + pad * 0.95), rotation=90, ha="left", va="top", fontsize=8, color="#213f75")

    fig.autofmt_xdate()
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)

# --- fetch when needed ---
if fetch_now or (auto_fetch and selection_changed):
    do_fetch()

# --- load the most recent raw file for this selection ---
raw_dir = Path("data/raw")
raw_files = sorted(raw_dir.glob(f"{product}_{station}_*.json"))

if not raw_files:
    st.info("No raw data yet. Click **Fetch / Refresh now** in the sidebar.")
    st.stop()

# Pick the raw file for the current window when present; otherwise use most recently modified.
start, end = compute_window(product, days)
expected_name = f"{product}_{station}_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.json"
expected_path = raw_dir / expected_name

if expected_path.exists():
    raw_path = expected_path
elif st.session_state.get("current_raw_path") and Path(st.session_state.current_raw_path).exists():
    raw_path = Path(st.session_state.current_raw_path)
else:
    raw_path = max(raw_files, key=lambda p: p.stat().st_mtime)

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
render_tide_chart(df)

if {"date", "sunrise_time", "sunset_time"}.issubset(set(df.columns)):
    sun_table = (
        df[["date", "sunrise_time", "sunset_time"]]
        .drop_duplicates(subset=["date"])
        .sort_values("date")
    )
    st.caption("Daily sun events")
    st.dataframe(sun_table, use_container_width=True)

with st.expander("Preview data (first 100 rows)"):
    st.dataframe(df.head(100))

st.download_button(
    "Download CSV",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name=f"tides_{product}_{station}.csv",
    mime="text/csv",
)
