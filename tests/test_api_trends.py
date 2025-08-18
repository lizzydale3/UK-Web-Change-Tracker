from __future__ import annotations

import types
import pandas as pd


def test_trends_vpn_endpoint_with_mock_pytrends(app_client, monkeypatch):
    # Build a tiny dataframe that resembles pytrends output
    dates = pd.date_range(start="2025-08-10", periods=5, freq="D")
    df = pd.DataFrame({"VPN": [50, 60, 55, 70, 65], "isPartial": [False, False, False, False, False]}, index=dates)

    class DummyTrendReq:
        def __init__(self, hl="en-US", tz=0):
            pass

        def build_payload(self, kw_list, geo, timeframe, gprop=""):
            self.kw_list = kw_list
            self.geo = geo
            self.timeframe = timeframe

        def interest_over_time(self):
            return df

    # Monkeypatch pytrends in the module import point
    monkeypatch.setitem(dict(globals()), "TrendReq", DummyTrendReq, raising=False)
    monkeypatch.setenv("FLASK_ENV", "testing")

    # Call API
    res = app_client.get("/api/trends/vpn?country=GB&days=5")
    assert res.status_code == 200
    body = res.get_json()
    assert body["ok"] is True
    assert body["country"] == "GB"
    assert len(body["series"]) == 5
    # Ensure numeric conversion occurred
    assert isinstance(body["series"][0]["value"], int)



