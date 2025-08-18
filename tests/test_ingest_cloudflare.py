from __future__ import annotations

import json

from app.ingest.cloudflare import fetch_http_requests, fetch_l3
from app.db.mongo import get_collection


def test_fetch_http_requests_inserts_points(fake_requests):
    # Arrange: mock Cloudflare HTTP endpoint with a minimal successful payload
    def mapper(url, headers, params):
        if url.endswith("/radar/http/timeseries"):
            payload = {
                "success": True,
                "result": {
                    "main": {
                        "timestamps": [
                            "2025-08-10T00:00:00Z",
                            "2025-08-11T00:00:00Z",
                        ],
                        "values": [1.0, 1.2],
                    }
                },
            }
            return payload, 200
        # default safeguard
        return {"success": True, "result": {}}, 200

    fake_requests(mapper)

    # Act
    n = fetch_http_requests("GB", interval="1d", days=2, debug=True)

    # Assert
    coll = get_collection("traffic_ts")
    docs = list(coll.find({"country": "GB", "metric": "http_requests_norm"}))
    assert n == 2
    assert len(docs) == 2
    assert {d["value"] for d in docs} == {1.0, 1.2}


def test_fetch_l3_inserts_points_target_and_origin(fake_requests):
    # Arrange: mock Layer3 endpoint; same payload serves both calls
    def mapper(url, headers, params):
        if url.endswith("/radar/attacks/layer3/timeseries"):
            series = [
                {"t": "2025-08-10T00:00:00Z", "value": 0.002},
                {"t": "2025-08-11T00:00:00Z", "value": 0.005},
            ]
            payload = {"success": True, "result": {"series": series}}
            return payload, 200
        return {"success": True, "result": {}}, 200

    fake_requests(mapper)

    # Act
    n_t = fetch_l3("GB", interval="1d", days=2, direction="target", debug=True)
    n_o = fetch_l3("GB", interval="1d", days=2, direction="origin", debug=True)

    # Assert
    coll = get_collection("l3_ts")
    docs_t = list(coll.find({"country": "GB", "metric": "l3_bytes_target"}))
    docs_o = list(coll.find({"country": "GB", "metric": "l3_bytes_origin"}))
    assert n_t == 2 and n_o == 2
    assert len(docs_t) == 2 and len(docs_o) == 2
    # values preserved
    assert {d["value"] for d in docs_t} == {0.002, 0.005}
    assert {d["value"] for d in docs_o} == {0.002, 0.005}



