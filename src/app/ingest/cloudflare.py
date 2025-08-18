# app/ingest/cloudflare.py
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

import requests

from app import config
from app.db.mongo import get_collection

# -----------------------------
# Cloudflare API Configuration
# -----------------------------
CF_BASE = config.CLOUDFLARE_API_BASE or "https://api.cloudflare.com/client/v4"
CF_TOKEN = config.CLOUDFLARE_API_TOKEN or os.getenv("CLOUDFLARE_API_TOKEN")


def _get_headers() -> Dict[str, str]:
    """Cloudflare auth header."""
    if not CF_TOKEN:
        raise RuntimeError("CLOUDFLARE_API_TOKEN is not set")
    return {"Authorization": f"Bearer {CF_TOKEN}"}


def _make_request(path: str, params: Dict[str, Any], debug: bool = False) -> Dict[str, Any]:
    """GET wrapper with Radar success checking."""
    url = f"{CF_BASE.rstrip('/')}/{path.lstrip('/')}"
    if debug:
        print(f"[CF] GET {url} {params}")
    r = requests.get(url, headers=_get_headers(), params=params, timeout=30)
    if debug:
        print(f"[CF] status {r.status_code}")
    r.raise_for_status()
    body = r.json()
    if debug:
        print(f"[CF] success={body.get('success')} errors={body.get('errors')}")
    if not body.get("success", False):
        raise RuntimeError(f"Cloudflare API error: {body.get('errors')}")
    return body.get("result") or {}


# -----------------------------
# Utilities
# -----------------------------
def _get_time_range(days: int) -> Tuple[str, str]:
    """Return (since_iso, until_iso) for last N days."""
    until = datetime.now(timezone.utc)
    since = until - timedelta(days=days)
    return since.isoformat(), until.isoformat()


def _parse_timeseries_data(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Normalize Radar shapes into: [{ts: <iso>, value: <float>}].
    Supports:
      - result.main.timestamps/values
      - result.timestamps/values
      - result.series | result.timeseries : [{t|ts|time|timestamp, value|requests.normalized|bitrate.value}]
    """
    if not isinstance(result, dict):
        return []

    # 1) main.timestamps / main.values
    main = result.get("main")
    if isinstance(main, dict) and "timestamps" in main and "values" in main:
        ts = main.get("timestamps") or []
        vals = main.get("values") or []
        out = []
        for t, v in zip(ts, vals):
            try:
                out.append({"ts": str(t), "value": float(v)})
            except Exception:
                pass
        return out

    # 2) root timestamps / values
    if "timestamps" in result and "values" in result:
        ts = result.get("timestamps") or []
        vals = result.get("values") or []
        out = []
        for t, v in zip(ts, vals):
            try:
                out.append({"ts": str(t), "value": float(v)})
            except Exception:
                pass
        return out

    # 3) series / timeseries (list of dicts)
    for key in ("series", "timeseries"):
        arr = result.get(key)
        if isinstance(arr, list):
            out = []
            for row in arr:
                if not isinstance(row, dict):
                    continue
                ts = row.get("t") or row.get("ts") or row.get("time") or row.get("timestamp")
                val = row.get("value")
                if val is None and isinstance(row.get("requests"), dict):
                    val = row["requests"].get("normalized") or row["requests"].get("value")
                if val is None and isinstance(row.get("bitrate"), dict):
                    val = row["bitrate"].get("value")
                if ts is not None and val is not None:
                    try:
                        out.append({"ts": str(ts), "value": float(val)})
                    except Exception:
                        pass
            if out:
                return out

    return []


def _store_timeseries_data(collection_name: str, country: str, metric: str, data: List[Dict[str, Any]]) -> int:
    """Upsert timeseries points into Mongo."""
    coll = get_collection(collection_name)
    upserted = 0
    ctry = country.upper()
    for p in data:
        ts = p.get("ts")
        val = p.get("value")
        if ts is None or val is None:
            continue
        try:
            res = coll.update_one(
                {"country": ctry, "metric": metric, "ts": ts},
                {"$set": {"value": float(val)}},
                upsert=True,
            )
            if res.upserted_id is not None or res.modified_count > 0:
                upserted += 1
        except Exception:
            # swallow individual point errors; keep going
            pass
    return upserted


# -----------------------------
# HTTP Requests (normalized)
# -----------------------------
def fetch_http_requests(country: str, days: int = 90, debug: bool = False) -> int:
    """
    Fetch HTTP requests (normalized index) for a country.
    Writes to collection: traffic_ts, metric: http_requests_norm
    """
    since, until = _get_time_range(days)
    params = {
        "name": "main",            # critical: normalized index
        "location": country.upper(),
        "dateStart": since,
        "dateEnd": until,
        "aggInterval": "1h",
        "format": "json",
    }
    if debug:
        print(f"[HTTP] Fetching {days}d for {country}")

    try:
        result = _make_request("/radar/http/timeseries", params, debug=debug)
    except Exception as e:
        if debug:
            print(f"[HTTP] dateStart/dateEnd failed, falling back to dateRange: {e}")
        params.pop("dateStart", None)
        params.pop("dateEnd", None)
        params["dateRange"] = f"{days}d"
        result = _make_request("/radar/http/timeseries", params, debug=debug)

    parsed = _parse_timeseries_data(result)
    if debug:
        print(f"[HTTP] parsed points: {len(parsed)}")
    return _store_timeseries_data("traffic_ts", country, "http_requests_norm", parsed)


def fetch_http_requests_range(country: str, since_date: str, until_date: str, debug: bool = False) -> int:
    """
    Fetch HTTP requests for the latest 30 days (Cloudflare API limitation).
    Ignores since_date/until_date parameters and fetches latest available data.
    """
    if debug:
        print(f"[HTTP] Fetching latest 30 days of data (Cloudflare API limitation)")
        print(f"[HTTP] Requested range {since_date} to {until_date} ignored")
    
    # Just fetch the latest 30 days that we know works
    return fetch_http_requests(country, days=30, debug=debug)


# -----------------------------
# Top Domains
# -----------------------------
def fetch_top_domains(country: str, date: str | None = None, debug: bool = False, limit: int = 100) -> int:
    """
    Fetch top domains snapshot; writes to domain_rank.
    """
    params = {
        "name": "top",
        "location": country.upper(),
        "limit": limit,
        "dateRange": "1d",
        "format": "json",
    }
    if date:
        params["date"] = date
    if debug:
        print(f"[Top] {country} limit={limit} date={date or 'latest'}")

    result = _make_request("/radar/ranking/top", params, debug=debug)
    rows = result.get("top") or result.get("items") or []
    if debug:
        print(f"[Top] rows={len(rows)}")

    coll = get_collection("domain_rank")
    upserted = 0
    eff_date = date or datetime.now(timezone.utc).date().isoformat()
    ctry = country.upper()

    for row in rows:
        domain = row.get("domain")
        rank = row.get("rank")
        cats = row.get("categories") or []
        cat_name = None
        if cats and isinstance(cats, list):
            first = cats[0]
            if isinstance(first, dict):
                cat_name = first.get("name")
        if not domain or rank is None:
            continue

        try:
            res = coll.update_one(
                {"country": ctry, "date": eff_date, "domain": domain},
                {"$set": {"rank": int(rank), "category": cat_name}},
                upsert=True,
            )
            if res.upserted_id is not None or res.modified_count > 0:
                upserted += 1
        except Exception:
            pass

    if debug:
        print(f"[Top] upserted={upserted}")
    return upserted


def fetch_top_domains_range(country: str, since_date: str, until_date: str, debug: bool = False, limit: int = 100) -> int:
    """Fetch top domains for the latest 7 days (Cloudflare API limitation)."""
    if debug:
        print(f"[Top] Fetching latest 7 days of top domains (Cloudflare API limitation)")
        print(f"[Top] Requested range {since_date} to {until_date} ignored")
    
    # Fetch top domains for the last 7 days (daily snapshots)
    from datetime import datetime, timedelta, timezone
    
    total = 0
    now = datetime.now(timezone.utc)
    
    for i in range(7):
        date = (now - timedelta(days=i)).date().isoformat()
        total += fetch_top_domains(country, date=date, debug=debug, limit=limit)
    
    if debug:
        print(f"[Top] total upserted across 7 days: {total}")
    return total


# -----------------------------
# Layer‑3 Attacks (bytes)
# -----------------------------
def fetch_l3_attacks(country: str, direction: str = "target", days: int = 90, debug: bool = False) -> int:
    """
    Fetch L3 mitigated bytes (target/origin). Writes to l3_ts as l3_bytes_<direction>.
    """
    since, until = _get_time_range(days)
    params = {
        "aggInterval": "1d",
        "location": country.upper(),
        "format": "json",
        "metric": "bytes",
        "direction": direction,
        "dateStart": since,
        "dateEnd": until,
    }
    if debug:
        print(f"[L3] {direction} {country} {days}d")

    try:
        result = _make_request("/radar/attacks/layer3/timeseries", params, debug=debug)
    except Exception as e:
        if debug:
            print(f"[L3] dateStart/dateEnd failed, dateRange fallback: {e}")
        params.pop("dateStart", None); params.pop("dateEnd", None)
        params["dateRange"] = f"{days}d"
        result = _make_request("/radar/attacks/layer3/timeseries", params, debug=debug)

    parsed = _parse_timeseries_data(result)
    if debug:
        print(f"[L3] parsed points: {len(parsed)}")
    metric_name = f"l3_bytes_{direction.lower()}"
    return _store_timeseries_data("l3_ts", country, metric_name, parsed)


def fetch_l3_attacks_range(country: str, since_date: str, until_date: str, direction: str = "target", debug: bool = False) -> int:
    """Fetch L3 attacks for the latest 30 days (Cloudflare API limitation)."""
    if debug:
        print(f"[L3] Fetching latest 30 days of L3 {direction} data (Cloudflare API limitation)")
        print(f"[L3] Requested range {since_date} to {until_date} ignored")
    
    # Just fetch the latest 30 days that we know works
    return fetch_l3_attacks(country, direction=direction, days=30, debug=debug)


# -----------------------------
# Bot Traffic
# -----------------------------
def fetch_bot_traffic(country: str, days: int = 30, debug: bool = False) -> int:
    """
    Fetch bot traffic share (Radar Bots timeseries). Writes to bot_traffic, metric: bot_traffic.
    """
    since, until = _get_time_range(days)
    params = {
        "aggInterval": "1d",
        "location": country.upper(),
        "format": "json",
        "dateStart": since,
        "dateEnd": until,
    }
    if debug:
        print(f"[Bots] {country} {days}d")

    try:
        result = _make_request("/radar/bots/timeseries", params, debug=debug)
    except Exception as e:
        if debug:
            print(f"[Bots] dateStart/dateEnd failed, dateRange fallback: {e}")
        params.pop("dateStart", None); params.pop("dateEnd", None)
        params["dateRange"] = f"{days}d"
        result = _make_request("/radar/bots/timeseries", params, debug=debug)

    parsed = _parse_timeseries_data(result)
    if debug:
        print(f"[Bots] parsed points: {len(parsed)}")
    return _store_timeseries_data("bot_traffic", country, "bot_traffic", parsed)


def fetch_bot_traffic_range(country: str, since_date: str, until_date: str, debug: bool = False) -> int:
    """Fetch bot traffic for the latest 30 days (Cloudflare API limitation)."""
    if debug:
        print(f"[Bots] Fetching latest 30 days of bot data (Cloudflare API limitation)")
        print(f"[Bots] Requested range {since_date} to {until_date} ignored")
    
    # Just fetch the latest 30 days that we know works
    return fetch_bot_traffic(country, days=30, debug=debug)


# -----------------------------
# Back-compat aliases
# -----------------------------
def fetch_http_requests_norm(country: str, days: int = 90, debug: bool = False) -> int:
    return fetch_http_requests(country, days, debug)


def fetch_l3(country: str, interval: str = "1d", days: int = 84, direction: str = "target", debug: bool = False) -> int:
    # interval kept for signature compatibility; Radar layer3 call above is daily.
    return fetch_l3_attacks(country, direction, days, debug)


def fetch_top_domains_ranked(country: str, date: str | None = None, debug: bool = False, limit: int = 100) -> int:
    return fetch_top_domains(country, date, debug, limit)
