from __future__ import annotations

import importlib
from flask import Blueprint

API_MODULES = [
    "health",
    "timeseries",
    "top_domains",
    "attacks",
    "age_gate",
    "ooni",
    "trends",
    "events",
]

def register_api(app):
    api_bp = Blueprint("api", __name__, url_prefix="/api")

    for name in API_MODULES:
        mod_qualname = f"{__name__}.{name}"
        try:
            mod = importlib.import_module(mod_qualname)
        except Exception as e:
            app.logger.warning("Skipping API module %s: %s", mod_qualname, e)
            continue

        bp = getattr(mod, "bp", None)
        if bp is None:
            app.logger.warning("Module %s has no `bp`; skipping", mod_qualname)
            continue
        api_bp.register_blueprint(bp)

    app.register_blueprint(api_bp)
