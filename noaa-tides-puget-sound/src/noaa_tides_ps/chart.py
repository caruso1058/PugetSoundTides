from __future__ import annotations
import argparse
from pathlib import Path
import sys
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.dates import AutoDateLocator, DateFormatter

# Uncomment if you hit GUI backend issues:
# matplotlib.use("Agg")

STATION_NAMES = {
    "9447130": "Seattle",
    "9446484": "Tacoma",
    "9444900": "Port Townsend",
    "9447659": "Everett",
}

def detect_peaks(s: pd.Series):
    prev, nxt = s.shift(1), s.shift(-1)
    highs = (s > prev) & (s > nxt)
    lows  = (s < prev) & (s < nxt)
    return highs.fillna(False), lows.fillna(False)

def plot_tide(csv_path: Path, out_path: Path, title: str, annotate: bool = True, debug: bool = False):
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    try:
        df = pd.read_csv(csv_path, parse_dates=["timestamp"])
    except Exception as e:
        raise RuntimeError(f"Failed to read CSV {csv_path}: {e}")

    # Basic schema checks
    required = {"timestamp", "tide_ft"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}. Columns present: {list(df.columns)}")

    if df.empty:
        raise ValueError("CSV has no rows after read")

    # Coerce types defensively
    df["tide_ft"] = pd.to_numeric(df["tide_ft"], errors="coerce")
    df = df.dropna(subset=["timestamp", "tide_ft"])
    if df.empty:
        raise ValueError("All rows became NaN after type coercion")

    if debug:
        print("Data preview:", file=sys.stderr)
        print(df.head(10).to_string(index=False), file=sys.stderr)
        print("dtypes:", df.dtypes.to_string(), file=sys.stderr)

    fig, ax = plt.subplots()
    ax.plot(df["timestamp"], df["tide_ft"], linewidth=2)
    ax.set_xlabel("Time")
    ax.set_ylabel("Tide (ft)")
    ax.set_title(title)

    locator = AutoDateLocator(minticks=4, maxticks=8)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(DateFormatter("%b %d\n%I:%M %p"))

    y_min, y_max = float(df["tide_ft"].min()), float(df["tide_ft"].max())
    pad = max(0.3, (y_max - y_min) * 0.10)
    ax.set_ylim(y_min - pad * 0.15, y_max + pad)

    if annotate and len(df) >= 3:
        highs, lows = detect_peaks(df["tide_ft"])

        def fmt_time(ts):
            return pd.to_datetime(ts).strftime("%I:%M %p").lstrip("0")

        for idx in df[highs].index:
            x = df.at[idx, "timestamp"]; y = df.at[idx, "tide_ft"]
            ax.scatter([x], [y])
            ax.annotate(fmt_time(x), (x, y),
                        textcoords="offset points", xytext=(0, 10),
                        ha="center", va="bottom", clip_on=True)

        for idx in df[lows].index:
            x = df.at[idx, "timestamp"]; y = df.at[idx, "tide_ft"]
            ax.scatter([x], [y])
            ax.annotate(fmt_time(x), (x, y),
                        textcoords="offset points", xytext=(0, 10),
                        ha="center", va="bottom", clip_on=True)

    fig.autofmt_xdate()
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150)
    print(f"Wrote chart: {out_path}")

def main():
    ap = argparse.ArgumentParser(description="Render a tide chart with time labels on highs/lows")
    ap.add_argument("--station", required=True, help="NOAA station id (e.g., 9447659)")
    ap.add_argument("--product", default="predictions", choices=["predictions", "water_level"])
    ap.add_argument("--csv", help="Explicit path to tidy CSV (optional)")
    ap.add_argument("--annotate", action="store_true", help="Label highs/lows with time")
    ap.add_argument("--debug", action="store_true", help="Print debug info")
    args = ap.parse_args()

    csv = Path(args.csv) if args.csv else Path(f"data/processed/tidy_{args.product}_{args.station}.csv")
    out = Path(f"docs/tide_{args.product}_{args.station}.png")
    station_label = STATION_NAMES.get(str(args.station), str(args.station))
    title = f"Tides – {station_label}"

    plot_tide(csv, out, title, annotate=args.annotate, debug=args.debug)

if __name__ == "__main__":
    main()
