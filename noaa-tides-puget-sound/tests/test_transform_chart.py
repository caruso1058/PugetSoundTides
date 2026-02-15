import json

import pandas as pd

from src.noaa_tides_ps.chart import detect_peaks
from src.noaa_tides_ps.transform import latest_raw_for_station, tidy_from_raw


def test_tidy_from_raw_predictions(tmp_path):
    raw = tmp_path / "predictions_9447130_20250101_20250101.json"
    payload = {
        "predictions": [
            {"t": "2025-01-01 00:00", "v": "7.1", "type": "H"},
            {"t": "2025-01-01 01:00", "v": "6.4", "type": "L"},
        ]
    }
    raw.write_text(json.dumps(payload))

    df = tidy_from_raw(raw, product="predictions")

    assert list(df["source"].unique()) == ["prediction"]
    assert df["tide_ft"].tolist() == [7.1, 6.4]
    assert df["hi_lo"].tolist() == ["H", "L"]
    assert "date" in df.columns
    assert "hour" in df.columns


def test_tidy_from_raw_water_level(tmp_path):
    raw = tmp_path / "water_level_9447130_20250101_20250101.json"
    payload = {"data": [{"t": "2025-01-01 00:06", "v": "5.23"}]}
    raw.write_text(json.dumps(payload))

    df = tidy_from_raw(raw, product="water_level")

    assert list(df["source"].unique()) == ["observation"]
    assert df["tide_ft"].tolist() == [5.23]
    assert df["hi_lo"].isna().all()


def test_latest_raw_for_station_uses_lexicographically_last(tmp_path):
    older = tmp_path / "predictions_9447130_20250101_20250102.json"
    newer = tmp_path / "predictions_9447130_20250103_20250104.json"
    older.write_text("{}")
    newer.write_text("{}")

    latest = latest_raw_for_station(tmp_path, "9447130", "predictions")

    assert latest == newer


def test_detect_peaks_flags_highs_and_lows():
    s = pd.Series([2.0, 4.0, 1.0, 3.0, 2.0])

    highs, lows = detect_peaks(s)

    assert highs.tolist() == [False, True, False, True, False]
    assert lows.tolist() == [False, False, True, False, False]
