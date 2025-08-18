from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from flask import Blueprint, jsonify, request

from app.db.mongo import get_collection
from app.analytics.windows import compute_window_stats

bp = Blueprint("api_timeseries", __name__)

def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _parse_int(name: str, default: int) -> int:
    try:
        return int(request.args.get(name, default))
    except Exception:
        return default

def _parse_csv(name: str, default: List[str]) -> List[str]:
    raw = request.args.get(name)
    if not raw:
        return default
    return [s.strip().upper() for s in raw.split(",") if s.strip()]

def _parse_iso(name: str) -> Optional[str]:
    v = request.args.get(name)
    return v if v else None

def _find_series(country: str, metric: str, since_iso: Optional[str], until_iso: Optional[str]) -> List[Dict]:
    """
    Return a list of {ts, value} sorted by ts (ISO strings).
    Handles both traffic_ts and l3_ts collections based on metric name.
    """
    # Determine which collection to query based on metric
    if metric.startswith("l3_"):
        coll = get_collection("l3_ts")
    elif metric.startswith("bot_"):
        coll = get_collection("bot_traffic")
    else:
        coll = get_collection("traffic_ts")
    
    q = {"country": country.upper(), "metric": metric}
    if since_iso or until_iso:
        tcrit: Dict[str, Dict[str, str]] = {}
        if since_iso:
            tcrit["$gte"] = since_iso
        if until_iso:
            tcrit["$lte"] = until_iso
        q["ts"] = tcrit
    cur = coll.find(q, {"_id": 0, "ts": 1, "value": 1}).sort("ts", 1)
    return list(cur)

@bp.get("/timeseries")
def get_timeseries():
    """
    GET /api/timeseries?country=GB&metric=http_requests_norm&days=30
    Optional: since=ISO until=ISO (overrides days), controls=IE,NL
    """
    country = request.args.get("country", "GB").upper()
    metric = request.args.get("metric", "http_requests_norm")
    days = _parse_int("days", 30)
    since = _parse_iso("since")
    until = _parse_iso("until")
    controls = _parse_csv("controls", [])

    # Default window if since/until not provided
    if not since or not until:
        until_dt = datetime.now(timezone.utc)
        since_dt = until_dt - timedelta(days=days)
        since = since_dt.isoformat()
        until = until_dt.isoformat()

    base = _find_series(country, metric, since, until)
    payload: Dict[str, object] = {
        "ok": True,
        "country": country,
        "metric": metric,
        "since": since,
        "until": until,
        "points": base,
        "time_utc": _iso_now(),
    }

    if controls:
        ctrl_map: Dict[str, List[Dict]] = {}
        for c in controls:
            ctrl_map[c] = _find_series(c, metric, since, until)
        payload["controls"] = ctrl_map

    return jsonify(payload)

@bp.get("/window-stats")
def window_stats():
    """
    GET /api/window-stats?country=GB&metric=http_requests_norm&event=2025-07-25&pre=14&post=14&controls=IE,NL
    Returns mean_pre, mean_post, pct_delta, and z-score vs synthetic control (avg of controls).
    """
    country = request.args.get("country", "GB").upper()
    metric = request.args.get("metric", "http_requests_norm")
    event = request.args.get("event")  # YYYY-MM-DD required
    if not event:
        return jsonify({"ok": False, "error": "missing 'event' (YYYY-MM-DD)"}), 400

    pre_days = _parse_int("pre", 14)
    post_days = _parse_int("post", 14)
    controls = _parse_csv("controls", [])

    stats = compute_window_stats(
        country=country,
        metric=metric,
        event=event,
        pre_days=pre_days,
        post_days=post_days,
        controls=controls or None,
    )
    stats.update({"ok": True, "time_utc": _iso_now()})
    return jsonify(stats)
