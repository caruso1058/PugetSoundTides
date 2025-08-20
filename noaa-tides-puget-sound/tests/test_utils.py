from src.noaa_tides_ps.fetch import build_url

def test_build_url_predictions():
    url = build_url("9447130","20250101","20250102",product="predictions")
    assert "product=predictions" in url and "interval=h" in url

def test_build_url_observations():
    url = build_url("9447130","20250101","20250102",product="water_level")
    assert "product=water_level" in url and "interval=" not in url
