# robust .env loading
import os
from pathlib import Path
try:
    from dotenv import load_dotenv  # type: ignore
    # 1) load from CWD (project root when you run commands there)
    load_dotenv(override=False)
    # 2) also try repo root even if code runs from src/
    repo_root = Path(__file__).resolve().parents[2]
    env_path = repo_root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
except Exception:
    pass

# --- Flask / server ---
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")
FLASK_ENV = os.getenv("FLASK_ENV", "production")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

# --- Encryption ---
FERNET_KEY = os.getenv("FERNET_KEY")  # optional: used by crypto.encrypt
HMAC_KEY = os.getenv("HMAC_KEY")      # optional: used by crypto helpers

# --- Cloudflare ---
CLOUDFLARE_API_BASE = os.getenv("CLOUDFLARE_API_BASE", "https://api.cloudflare.com/client/v4")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")

# --- MongoDB ---
MONGODB_URI = os.getenv("MONGODB_URI")
MONGO_DB = os.getenv("MONGO_DB", "internet_tracker")

# --- Defaults for analysis ---
DEFAULT_COUNTRY = os.getenv("COUNTRIES", "GB")
DEFAULT_EVENT_DATE = os.getenv("EVENT_DATE", "2025-07-25")

# --- Event registry (country + event_date + optional Tor PNG) ---
EVENTS = [
    {"slug":"uk-age-verify-2025","name":"UK Age Verification (2025-07-25)","country":"GB","event_date":"2025-07-25","tor_pngs": [
        {"label": "Tor Relay Users (GB)", "url": "https://metrics.torproject.org/userstats-relay-country.png?start=2024-12-01&end=2025-08-15&country=gb&events=off"},
        {"label": "Tor Bridge Users (GB)", "url": "https://metrics.torproject.org/userstats-bridge-country.png?start=2024-12-01&end=2025-08-15&country=gb"},
        {"label": "Tor Relay Users (Global)", "url": "https://metrics.torproject.org/userstats-relay-country.png?start=2024-12-01&end=2025-08-15&country=all&events=off"},
        {"label": "Tor Bridge Users (Global)", "url": "https://metrics.torproject.org/userstats-bridge-country.png?start=2024-12-01&end=2025-08-15&country=all"}
    ]}
]

DEFAULT_EVENT_SLUG = "uk-age-verify-2025"

def get_event(slug: str | None):
    if not slug:
        slug = DEFAULT_EVENT_SLUG
    for e in EVENTS:
        if e["slug"] == slug:
            return e
    # fallback to first if unknown slug
    return EVENTS[0]

# (existing) defaults still used by APIs/ingesters
DEFAULT_COUNTRY = os.getenv("COUNTRIES", "GB").split(",")[0].upper()
DEFAULT_EVENT_DATE = os.getenv("EVENT_DATE", "2025-07-25")
