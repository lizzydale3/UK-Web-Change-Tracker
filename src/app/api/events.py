from __future__ import annotations
from flask import Blueprint, jsonify, request
from app import config

bp = Blueprint("api_events", __name__)

@bp.get("/events")
def list_events():
    """
    GET /api/events
    Returns the configured event registry.
    """
    return jsonify({"ok": True, "events": config.EVENTS})

@bp.get("/event")
def get_event():
    """
    GET /api/event?slug=uk-age-verify-2025
    Resolves a single event object (falls back to default if slug missing/unknown).
    """
    slug = request.args.get("slug")
    ev = config.get_event(slug)
    return jsonify({"ok": True, "event": ev})
