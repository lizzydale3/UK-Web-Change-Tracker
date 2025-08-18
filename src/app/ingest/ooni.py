from __future__ import annotations

from datetime import date, timedelta
from typing import Dict, List, Tuple

import requests

from app.db.mongo import get_collection

BASE = "https://api.ooni.io/api/v1/aggregation"  # singular endpoint

# OONI test names we care about
TOOLS = ["tor", "snowflake", "psiphon"]

def _pick_rows(payload: dict) -> List[dict]:
    """
    OONI sometimes returns `result`, sometimes `results`.
    Normalize to a list.
    """
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("result"), list):
        return payload["result"]
    if isinstance(payload.get("results"), list):
        return payload["results"]
    # Some responses nest under 'data' or similar; be tolerant
    for k in ("data", "items"):
        if isinstance(payload.get(k), list):
            return payload[k]
    return []


def fetch_ooni(country: str = "GB", days: int = 120, debug: bool = False) -> int:
    """
    Fetch daily ok_rate per tool for a country and upsert into `ooni_tool_ok`.
    ok_rate = ok_count / measurement_count (if measurement_count > 0)
    """
    col = get_collection("ooni_tool_ok")
    end = date.today()
    start = end - timedelta(days=days)

    total_upserts = 0

    for tool in TOOLS:
        params = {
            "probe_cc": country.upper(),
            "test_name": tool,
            "since": start.isoformat(),
            "until": end.isoformat(),
            "axis_x": "measurement_start_day",
            "format": "JSON",
        }
        if debug:
            print("[OONI] GET", BASE, params)
        r = requests.get(BASE, params=params, timeout=30)
        if debug:
            print("[OONI] status", r.status_code)
        try:
            r.raise_for_status()
            payload = r.json()
        except Exception as e:
            if debug:
                print(f"[OONI] fetch failed for {tool}: {e}")
            continue

        rows = _pick_rows(payload)
        upserts_for_tool = 0

        for row in rows:
            day = (
                row.get("bucket_date")
                or row.get("measurement_start_day")
                or (row.get("measurement_start_time", "")[:10] if row.get("measurement_start_time") else None)
            )
            tests_count = int(row.get("measurement_count", row.get("total", 0)) or 0)
            ok = int(row.get("ok_count", row.get("confirmed_count", 0)) or 0)
            ok_rate = (ok / tests_count) if tests_count else None
            if not day:
                continue
            doc = {
                "date": day,
                "country": country.upper(),
                "tool": tool,
                "ok": ok,
                "tests": tests_count,
                "ok_rate": ok_rate,
            }
            col.update_one({"date": day, "country": country.upper(), "tool": tool}, {"$set": doc}, upsert=True)
            upserts_for_tool += 1

        total_upserts += upserts_for_tool
        if debug:
            print(f"[OONI] tool={tool} days={len(rows)} upserts={upserts_for_tool}")

    return total_upserts
