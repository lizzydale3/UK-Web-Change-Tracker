from __future__ import annotations
import os
from datetime import datetime, timezone
from flask import Blueprint, jsonify

from app import config
from app.db.mongo import get_db, ping

bp = Blueprint("api_health", __name__)

@bp.get("/health")
def health():
    db_ok = ping()
    now = datetime.now(timezone.utc).isoformat()

    return jsonify({
        "ok": True,
        "time_utc": now,
        "env": {
            "flask_env": os.getenv("FLASK_ENV", "production"),
            "cors_origins": os.getenv("CORS_ORIGINS", "*"),
        },
        "config": {
            "default_country": config.DEFAULT_COUNTRY,
            "event_date": config.DEFAULT_EVENT_DATE,
            "mongo_db": config.MONGO_DB,
            "cf_api_base": config.CLOUDFLARE_API_BASE,
            "cf_token_set": bool(config.CLOUDFLARE_API_TOKEN),
        },
        "db": {
            "ping": db_ok,
        }
    })

@bp.get("/debug-counts")
def debug_counts():
    """
    Counts for core collections to quickly verify ingestion.
    Safe even if collections are empty/missing.
    """
    db = get_db()
    def count(name: str) -> int:
        try:
            return db[name].estimated_document_count()
        except Exception:
            return 0

    return jsonify({
        "domain_rank": count("domain_rank"),
        "traffic_ts": count("traffic_ts"),
        "l3_ts": count("l3_ts"),
        "ooni_tool_ok": count("ooni_tool_ok"),
        "age_gate": count("age_gate"),
    })
