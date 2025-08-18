import os
from flask import Flask
from flask_cors import CORS

def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    CORS(app, origins=os.getenv("CORS_ORIGINS", "*"))

    # Ensure DB indexes early (safe to run multiple times)
    try:
        from app.db.mongo import ensure_indexes  # type: ignore
        ensure_indexes()
    except Exception as e:
        app.logger.warning(f"[create_app] ensure_indexes skipped: {e}")

    # Register blueprints
    try:
        from app.api import register_api  # type: ignore
        register_api(app)
    except Exception as e:
        app.logger.warning(f"[create_app] API not registered yet: {e}")

    try:
        from app.web import register_web  # type: ignore
        register_web(app)
    except Exception as e:
        app.logger.warning(f"[create_app] Web not registered yet: {e}")

    return app
