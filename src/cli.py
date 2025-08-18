# src/cli.py
from __future__ import annotations

import os
import sys
import json
import argparse
import traceback

# Ensure our package is importable regardless of CWD
sys.path.insert(0, os.path.dirname(__file__))

# ---------------------------
# Commands
# ---------------------------

def cmd_serve(port: int, host: str, debug: bool):
    from app import create_app
    app = create_app()
    app.run(host=host, port=port, debug=debug)


def cmd_db_ping() -> None:
    from app.db.mongo import ping
    ok = ping()
    print("mongo ping:", "ok" if ok else "failed")
    if not ok:
        raise SystemExit(2)


def cmd_fetch_cloudflare(
    kind: str,
    country: str,
    interval: str,
    days: int,
    limit: int,
    date: str | None,
    direction: str,
    debug: bool,
):
    """
    kind: top | http | l3 | bots
    """
    from app.ingest.cloudflare import (
        fetch_top_domains,
        fetch_http_requests,
        fetch_l3,
        fetch_bot_traffic,
    )

    cc = country.upper()

    if kind == "top":
        n = fetch_top_domains(cc, limit=limit, date=date, debug=debug)
        print(f"Upserted {n} domain_rank rows")
        return

    if kind == "http":
        n = fetch_http_requests(cc, days=days, debug=debug)
        print(f"Upserted {n} traffic_ts rows")
        return

    if kind == "l3":
        # NOTE: fetch_l3 must accept `direction` in your ingest module per our latest patch.
        n = fetch_l3(cc, interval=(interval or "1d"), days=days, direction=direction, debug=debug)
        print(f"Upserted {n} l3_ts rows")
        return

    if kind == "bots":
        n = fetch_bot_traffic(cc, days=days, debug=debug)
        print(f"Upserted {n} bot_traffic rows")
        return

    raise SystemExit("--kind must be one of: top|http|l3|bots")


def cmd_fetch_cloudflare_range(
    kind: str,
    country: str,
    since_date: str,
    until_date: str,
    limit: int,
    direction: str,
    debug: bool,
):
    """
    Fetch data over a specific date range.
    kind: top | http | l3 | bots
    since_date and until_date should be in YYYY-MM-DD format
    """
    from app.ingest.cloudflare import (
        fetch_top_domains_range,
        fetch_http_requests_range,
        fetch_l3_attacks_range,
        fetch_bot_traffic_range,
    )

    cc = country.upper()

    if kind == "top":
        n = fetch_top_domains_range(cc, since_date, until_date, debug=debug, limit=limit)
        print(f"Upserted {n} domain_rank rows across date range")
        return

    if kind == "http":
        n = fetch_http_requests_range(cc, since_date, until_date, debug=debug)
        print(f"Upserted {n} traffic_ts rows across date range")
        return

    if kind == "l3":
        n = fetch_l3_attacks_range(cc, since_date, until_date, direction=direction, debug=debug)
        print(f"Upserted {n} l3_ts rows across date range")
        return

    if kind == "bots":
        n = fetch_bot_traffic_range(cc, since_date, until_date, debug=debug)
        print(f"Upserted {n} bot_traffic rows across date range")
        return

    raise SystemExit("--kind must be one of: top|http|l3|bots")


def cmd_fetch_ooni(country: str, days: int, debug: bool):
    from app.ingest.ooni import fetch_ooni
    n = fetch_ooni(country.upper(), days=days, debug=debug)
    print(f"Upserted {n} ooni_ts rows")


def cmd_events():
    # Pretty-print the event registry to verify wiring
    from app import config
    try:
        print(json.dumps({"ok": True, "events": getattr(config, "EVENTS", [])}, indent=2))
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        raise


def cmd_secret(action: str, value: str | None, hmac_flag: bool):
    # Helpers for generating keys or encrypt/decrypt text
    # (optional convenience, wired to app.crypto.encrypt)
    if action == "gen-key":
        if hmac_flag:
            import secrets
            print(secrets.token_hex(32))
        else:
            from app.crypto.encrypt import generate_fernet_key
            print(generate_fernet_key())
        return

    if action == "encrypt":
        if not value:
            raise SystemExit("secret encrypt requires a value")
        from app.crypto.encrypt import encrypt_str
        print(encrypt_str(value))
        return

    if action == "decrypt":
        if not value:
            raise SystemExit("secret decrypt requires a value")
        from app.crypto.encrypt import decrypt_str
        print(decrypt_str(value))
        return

    raise SystemExit("unknown secret action")


# ---------------------------
# Parser / main
# ---------------------------

def main():
    p = argparse.ArgumentParser(description="Web Change Tracker CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    # serve
    sp = sub.add_parser("serve", help="Run Flask server")
    sp.add_argument("--port", type=int, default=int(os.getenv("PORT", "8080")))
    sp.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"))
    sp.add_argument("--debug", action="store_true")
    sp.set_defaults(func=lambda a: cmd_serve(a.port, a.host, a.debug))

    # db
    sc = sub.add_parser("db", help="Database utilities")
    sc_sub = sc.add_subparsers(dest="dbcmd", required=True)
    scp = sc_sub.add_parser("ping", help="Ping MongoDB")
    scp.set_defaults(func=lambda a: cmd_db_ping())

    # cloudflare
    cf = sub.add_parser("fetch-cloudflare", help="Cloudflare ingest (top|http|l3|bots)")
    cf.add_argument("--kind", required=True, choices=["top", "http", "l3", "bots"])
    cf.add_argument("--country", default="GB")
    cf.add_argument("--interval", default="1h", choices=["1h", "1d"])
    cf.add_argument("--days", type=int, default=14)
    cf.add_argument("--limit", type=int, default=50)
    cf.add_argument("--date", default=None, help="YYYY-MM-DD for top domains")
    cf.add_argument("--direction", default="target", choices=["target", "origin"],
                    help="L3: attacks targeting or originating from country (default: target)")
    cf.add_argument("--debug", action="store_true")
    cf.set_defaults(func=lambda a: cmd_fetch_cloudflare(
        a.kind, a.country, a.interval, a.days, a.limit, a.date, a.direction, a.debug
    ))

    # cloudflare range
    cfr = sub.add_parser("fetch-cloudflare-range", help="Cloudflare ingest (top|http|l3|bots) over a date range")
    cfr.add_argument("--kind", required=True, choices=["top", "http", "l3", "bots"])
    cfr.add_argument("--country", default="GB")
    cfr.add_argument("--since-date", required=True, help="YYYY-MM-DD")
    cfr.add_argument("--until-date", required=True, help="YYYY-MM-DD")
    cfr.add_argument("--limit", type=int, default=50)
    cfr.add_argument("--direction", default="target", choices=["target", "origin"],
                    help="L3: attacks targeting or originating from country (default: target)")
    cfr.add_argument("--debug", action="store_true")
    cfr.set_defaults(func=lambda a: cmd_fetch_cloudflare_range(
        a.kind, a.country, a.since_date, a.until_date, a.limit, a.direction, a.debug
    ))

    # ooni
    so = sub.add_parser("fetch-ooni", help="OONI reachability (tor/snowflake/psiphon) daily ok_rate")
    so.add_argument("--country", default="GB")
    so.add_argument("--days", type=int, default=120)
    so.add_argument("--debug", action="store_true")
    so.set_defaults(func=lambda a: cmd_fetch_ooni(a.country, a.days, a.debug))

    # events
    ev = sub.add_parser("events", help="Print configured events registry")
    ev.set_defaults(func=lambda a: cmd_events())

    # secret
    ss = sub.add_parser("secret", help="Fernet/HMAC helpers")
    ss_sub = ss.add_subparsers(dest="action", required=True)
    gk = ss_sub.add_parser("gen-key"); gk.add_argument("--hmac", action="store_true")
    enc = ss_sub.add_parser("encrypt"); enc.add_argument("value")
    dec = ss_sub.add_parser("decrypt"); dec.add_argument("value")
    ss.set_defaults(func=lambda a: cmd_secret(a.action, getattr(a, "value", None), getattr(a, "hmac", False)))

    args = p.parse_args()
    try:
        return args.func(args)
    except Exception as e:
        # Surface trace on CLI errors
        print("ERROR:", e)
        traceback.print_exc()
        raise SystemExit(1)


if __name__ == "__main__":
    main()
