from __future__ import annotations

import os
import logging
from typing import Optional

from pymongo import MongoClient
try:
    # Optional, matches Atlas “Stable API v1” example (safe to omit if unavailable)
    from pymongo.server_api import ServerApi  # type: ignore
    _SERVER_API = ServerApi("1")
except Exception:  # older pymongo
    _SERVER_API = None  # type: ignore

# Always go through app.config so python-dotenv is applied
from app import config

_CLIENT: Optional[MongoClient] = None


def _mongo_uri() -> str:
    # Prefer config (loads .env), fallback to raw env
    uri = getattr(config, "MONGODB_URI", None) or os.getenv("MONGODB_URI")
    if not uri:
        raise RuntimeError("MONGODB_URI is not set")
    return uri


def _db_name() -> str:
    name = getattr(config, "MONGO_DB", None) or os.getenv("MONGO_DB") or "internet_tracker"
    return name


def get_client() -> MongoClient:
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    uri = _mongo_uri()
    kwargs = {"serverSelectionTimeoutMS": 5000}
    if _SERVER_API is not None:
        kwargs["server_api"] = _SERVER_API  # type: ignore
    _CLIENT = MongoClient(uri, **kwargs)
    return _CLIENT


def get_db():
    return get_client()[_db_name()]


def get_collection(name: str):
    return get_db()[name]


def ping() -> bool:
    try:
        get_client().admin.command("ping")
        return True
    except Exception as e:
        logging.error("Mongo ping failed: %s", e)
        return False


def ensure_indexes(logger: Optional[logging.Logger] = None) -> None:
    """
    Safe to call on startup; creates a few basic indexes if they don’t exist.
    """
    try:
        db = get_db()
    except Exception as e:
        (logger or logging).warning("[ensure_indexes] skipped: %s", e)
        return

    idx = {
        "domain_rank": [("country", 1), ("date", 1), ("rank", 1)],
        "traffic_ts": [("country", 1), ("metric", 1), ("ts", 1)],
        "l3_ts": [("country", 1), ("metric", 1), ("ts", 1)],
        "bot_traffic": [("country", 1), ("metric", 1), ("ts", 1)],
        "ooni_tool_ok": [("country", 1), ("tool", 1), ("date", 1)],
    }
    for coll, keys in idx.items():
        try:
            db[coll].create_index(keys)
        except Exception as e:
            (logger or logging).warning("index create failed for %s: %s", coll, e)
