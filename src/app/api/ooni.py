from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from flask import Blueprint, jsonify, request

from app.db.mongo import get_collection

bp = Blueprint("api_ooni", __name__)

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _parse_int(name: str, default: int) -> int:
    try:
        return int(request.args.get(name, default))
    except Exception:
        return int(default)

def _parse_csv(name: str, default: List[str]) -> List[str]:
    raw = request.args.get(name)
    if not raw:
        return default
    return [s.strip().lower() for s in raw.split(",") if s.strip()]

def _parse_iso(name: str) -> Optional[str]:
    v = request.args.get(name)
    return v if v else None

@bp.get("/ooni/tor")
def tor_reachability():
    """
    GET /api/ooni/tor?country=GB&days=180
    Returns Tor reachability data for the frontend charts.
    Special case: country=ALL returns global data for last 365 days.
    """
    country = request.args.get("country", "GB").upper()
    days = _parse_int("days", 180)
    
    # Special case: global data for last 365 days
    if country == "ALL":
        days = 365
    
    # Default window
    until_dt = datetime.now(timezone.utc).date()
    since_dt = until_dt - timedelta(days=days)
    since = since_dt.isoformat()
    until = until_dt.isoformat()

    coll = get_collection("ooni_tool_ok")
    
    # For global data, query without country filter
    if country == "ALL":
        q = {
            "tool": "tor",
            "date": {"$gte": since, "$lte": until},
        }
    else:
        q = {
            "country": country,
            "tool": "tor",
            "date": {"$gte": since, "$lte": until},
        }
    
    cur = coll.find(q, {"_id": 0, "date": 1, "ok": 1, "tests": 1, "ok_rate": 1}).sort("date", 1)
    results = list(cur)
    
    return jsonify({
        "ok": True,
        "country": country,
        "results": results,
        "since": since,
        "until": until,
        "time_utc": _iso_now(),
    })

@bp.get("/ooni/reachability")
def reachability():
    """
    GET /api/ooni/reachability?country=GB&tools=tor,snowflake,psiphon&days=120
    Optional: since=YYYY-MM-DD&until=YYYY-MM-DD (overrides days)
    Returns per-tool daily ok/tests/ok_rate series.
    """
    country = request.args.get("country", "GB").upper()
    tools   = _parse_csv("tools", ["tor", "snowflake", "psiphon"])
    days    = _parse_int("days", 120)
    since   = _parse_iso("since")
    until   = _parse_iso("until")

    # Default window
    if not since or not until:
        until_dt = datetime.now(timezone.utc).date()
        since_dt = until_dt - timedelta(days=days)
        since = since_dt.isoformat()
        until = until_dt.isoformat()

    coll = get_collection("ooni_tool_ok")
    series: Dict[str, List[Dict]] = {}

    for tool in tools:
        q: Dict = {
            "country": country,
            "tool": tool,
            "date": {"$gte": since, "$lte": until},  # date is stored as YYYY-MM-DD string
        }
        cur = coll.find(q, {"_id": 0, "date": 1, "ok": 1, "tests": 1, "ok_rate": 1}).sort("date", 1)
        series[tool] = list(cur)

    # Optional tiny summary: latest ok_rate per tool (if any)
    latest: Dict[str, Optional[float]] = {}
    for tool, rows in series.items():
        latest[tool] = rows[-1]["ok_rate"] if rows else None

    return jsonify({
        "ok": True,
        "country": country,
        "tools": tools,
        "since": since,
        "until": until,
        "series": series,
        "latest_ok_rate": latest,
        "time_utc": _iso_now(),
    })
