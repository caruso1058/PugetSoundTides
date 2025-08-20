from __future__ import annotations
import argparse, json
from pathlib import Path
import pandas as pd

def tidy_from_raw(raw_path: Path, product: str) -> pd.DataFrame:
    payload = json.loads(raw_path.read_text())
    if product == "predictions":
        df = pd.DataFrame(payload.get("predictions", []))
        if df.empty: return df
        df = df.rename(columns={"t":"timestamp","v":"tide_ft","type":"hi_lo"})
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["tide_ft"] = pd.to_numeric(df["tide_ft"], errors="coerce")
        df["source"] = "prediction"
    else:
        df = pd.DataFrame(payload.get("data", []))
        if df.empty: return df
        df = df.rename(columns={"t":"timestamp","v":"tide_ft"})
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["tide_ft"] = pd.to_numeric(df["tide_ft"], errors="coerce")
        df["hi_lo"] = None
        df["source"] = "observation"
    df["date"] = df["timestamp"].dt.date
    df["hour"] = df["timestamp"].dt.hour
    return df

def latest_raw_for_station(raw_dir: Path, station: str, product: str) -> Path:
    files = sorted(raw_dir.glob(f"{product}_{station}_*.json"))
    if not files:
        raise FileNotFoundError(f"No raw files for station {station} product {product}")
    return files[-1]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--station", required=True)
    p.add_argument("--product", default="predictions", choices=["predictions","water_level"])
    p.add_argument("--raw"); p.add_argument("--out_csv")
    a = p.parse_args()
    raw = Path(a.raw) if a.raw else latest_raw_for_station(Path("data/raw"), a.station, a.product)
    df = tidy_from_raw(raw, product=a.product)
    if df.empty: 
        print("No data"); return
    out_dir = Path("data/processed"); out_dir.mkdir(parents=True, exist_ok=True)
    out = Path(a.out_csv) if a.out_csv else out_dir / f"tidy_{a.product}_{a.station}.csv"
    df.to_csv(out, index=False)
    print(f"Wrote tidy CSV: {out} ({len(df)} rows)")

if __name__ == "__main__":
    main()
