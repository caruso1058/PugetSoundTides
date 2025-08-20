from __future__ import annotations
import argparse, datetime as dt
from pathlib import Path
from typing import Dict, Any
import requests, json

BASE_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"

def build_url(
    station: str,
    begin_date: str,
    end_date: str,
    product: str = "predictions",  # or "water_level"
    datum: str = "MLLW",
    time_zone: str = "lst_ldt",
    units: str = "english",
    interval: str = "h",
    fmt: str = "json",
) -> str:
    params: Dict[str, Any] = {
        "product": product,
        "application": "noaa-tides-ps",
        "begin_date": begin_date,
        "end_date": end_date,
        "datum": datum,
        "station": station,
        "time_zone": time_zone,
        "units": units,
        "format": fmt,
    }
    if product == "predictions":
        params["interval"] = interval
    q = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{BASE_URL}?{q}"

def fetch(station: str, start: dt.date, end: dt.date, out_dir: Path, product: str = "predictions") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    b, e = start.strftime("%Y%m%d"), end.strftime("%Y%m%d")
    url = build_url(station, b, e, product=product)
    r = requests.get(url, timeout=30); r.raise_for_status()
    data = r.json()
    key = "predictions" if product == "predictions" else "data"
    if key not in data:
        raise RuntimeError(f"Unexpected API response keys: {list(data.keys())}")
    out_path = out_dir / f"{product}_{station}_{b}_{e}.json"
    out_path.write_text(json.dumps(data, indent=2))
    return out_path

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--station", required=True)
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--start"); p.add_argument("--end")
    p.add_argument("--product", default="predictions", choices=["predictions","water_level"])
    a = p.parse_args()
    if a.start:
        start = dt.datetime.strptime(a.start,"%Y-%m-%d").date()
        end = dt.datetime.strptime(a.end,"%Y-%m-%d").date() if a.end else start
    else:
        start = dt.date.today(); end = start + dt.timedelta(days=max(0, a.days-1))
    path = fetch(a.station, start, end, Path("data/raw"), product=a.product)
    print(f"Wrote raw: {path}")

if __name__ == "__main__":
    main()
