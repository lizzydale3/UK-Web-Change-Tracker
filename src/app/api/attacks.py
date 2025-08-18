from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from flask import Blueprint, jsonify, request

from app.db.mongo import get_collection

bp = Blueprint("api_attacks", __name__)

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _parse_int(name: str, default: int) -> int:
    try:
        return int(request.args.get(name, default))
    except Exception:
        return default

def _parse_iso(name: str) -> Optional[str]:
    v = request.args.get(name)
    return v if v else None

@bp.get("/attacks")
def get_attacks():
    """
    GET /api/attacks?country=GB&metric=l3_bps&days=30
    Optional: since=ISO until=ISO (overrides days), interval=1d (for UI hints only)
    """
    country = request.args.get("country", "GB").upper()
    metric  = request.args.get("metric", "l3_bps")
    days    = _parse_int("days", 30)
    since   = _parse_iso("since")
    until   = _parse_iso("until")
    interval = request.args.get("interval", "1d")  # passthrough info for charts

    # Default window if since/until not provided
    if not since or not until:
        until_dt = datetime.now(timezone.utc)
        since_dt = until_dt - timedelta(days=days)
        since = since_dt.isoformat()
        until = until_dt.isoformat()

    coll = get_collection("l3_ts")
    q: Dict = {"country": country, "metric": metric, "ts": {"$gte": since, "$lte": until}}
    cur = coll.find(q, {"_id": 0, "ts": 1, "value": 1}).sort("ts", 1)
    points: List[Dict] = list(cur)

    return jsonify({
        "ok": True,
        "country": country,
        "metric": metric,
        "since": since,
        "until": until,
        "interval": interval,
        "points": points,
        "count": len(points),
        "time_utc": _iso_now(),
    })
