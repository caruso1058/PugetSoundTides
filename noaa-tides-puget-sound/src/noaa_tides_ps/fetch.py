from __future__ import annotations
import argparse, datetime as dt
from pathlib import Path
from typing import Dict, Any, Union
import requests, json
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

BASE_URL = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
SUN_API_URL = "https://api.sunrise-sunset.org/json"

STATION_COORDS: Dict[str, Dict[str, Union[str, float]]] = {
    "9447130": {"name": "Seattle", "lat": 47.6026, "lng": -122.3393, "tz": "US/Pacific"},
    "9446484": {"name": "Tacoma", "lat": 47.2669, "lng": -122.4134, "tz": "US/Pacific"},
    "9444900": {"name": "Port Townsend", "lat": 48.1114, "lng": -122.7596, "tz": "US/Pacific"},
    "9447659": {"name": "Everett", "lat": 47.9747, "lng": -122.2216, "tz": "US/Pacific"},
    "9443090": {"name": "Neah Bay", "lat": 48.3652, "lng": -124.6246, "tz": "US/Pacific"},
}

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
    data["sun_events"] = fetch_sun_events(station=station, start=start, end=end)
    out_path = out_dir / f"{product}_{station}_{b}_{e}.json"
    out_path.write_text(json.dumps(data, indent=2))
    return out_path


def fetch_sun_events(station: str, start: dt.date, end: dt.date) -> list[Dict[str, str]]:
    meta = STATION_COORDS.get(str(station))
    if not meta or ZoneInfo is None:
        return []

    tz = ZoneInfo(str(meta["tz"]))
    events: list[Dict[str, str]] = []
    day = start

    while day <= end:
        params = {
            "lat": meta["lat"],
            "lng": meta["lng"],
            "date": day.isoformat(),
            "formatted": 0,
        }
        try:
            resp = requests.get(SUN_API_URL, params=params, timeout=20)
            resp.raise_for_status()
            payload = resp.json()
            results = payload.get("results", {})
            sunrise_utc = dt.datetime.fromisoformat(results["sunrise"])
            sunset_utc = dt.datetime.fromisoformat(results["sunset"])
            sunrise_local = sunrise_utc.astimezone(tz)
            sunset_local = sunset_utc.astimezone(tz)
            events.append(
                {
                    "date": day.isoformat(),
                    "sunrise": sunrise_local.isoformat(),
                    "sunset": sunset_local.isoformat(),
                }
            )
        except Exception:
            # Keep tide fetch resilient if sun API is unavailable for a day.
            pass
        day += dt.timedelta(days=1)

    return events

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
