from __future__ import annotations

from typing import Dict, Optional

from flask import Blueprint, jsonify, request

from app.analytics.joiners import top_domains_for_day, top_domains_with_age_gate

bp = Blueprint("api_top_domains", __name__)


def _parse_limit(default: int = 10) -> int:
    try:
        n = int(request.args.get("limit", default))
        return max(1, min(n, 100))
    except Exception:
        return default


@bp.get("/top-domains")
def top_domains():
    """
    GET /api/top-domains?country=GB&date=YYYY-MM-DD&limit=10[&category=adult]
    If no date provided, serves the most recent day available for that country.
    """
    country = request.args.get("country", "GB").upper()
    date = request.args.get("date")  # YYYY-MM-DD or None (-> latest)
    category = request.args.get("category")  # optional filter
    limit = _parse_limit(10)

    resolved_date, rows = top_domains_for_day(
        country=country, date=date, limit=limit, category=category
    )

    payload: Dict[str, object] = {
        "ok": True,
        "country": country,
        "date": resolved_date,
        "limit": limit,
        "category": category,
        "results": rows,
        "count": len(rows),
    }
    # If no data, still return ok=True with empty results; client can handle "date": None
    return jsonify(payload)


@bp.get("/top-domains/age-gated")
def top_domains_age_gated():
    """
    GET /api/top-domains/age-gated?country=GB&date=YYYY-MM-DD&limit=10
    Annotates the (optionally filtered) top list with curated age-gate status.
    """
    country = request.args.get("country", "GB").upper()
    date = request.args.get("date")
    category = request.args.get("category")  # optional filter
    limit = _parse_limit(10)

    joined = top_domains_with_age_gate(
        country=country, date=date, limit=limit, category=category
    )
    joined.update({"ok": True, "limit": limit, "category": category})
    return jsonify(joined)
