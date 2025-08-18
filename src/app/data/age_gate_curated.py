"""
Curated age-gating status for well-known platforms.
Status:
  - "yes"     : requires age verification / gated for UK users
  - "no"      : explicitly not gated
  - "unknown" : unclear / mixed / not confirmed
Notes are optional and purely informational for UI.

This is intentionally tiny and editable. Extend as you learn more.
"""

CURATED: dict[str, dict[str, str | None]] = {
    # Social / Community
    "reddit.com":   {"status": "yes",     "note": "Reports of UK age checks after 2025-07-25"},
    "x.com":        {"status": "yes",     "note": "X/Twitter age verification prompts reported in UK"},
    "twitter.com":  {"status": "yes",     "note": "Alias for X"},
    "discord.com":  {"status": "yes",     "note": "Community platform; UK checks reported"},
    "bsky.app":     {"status": "yes",     "note": "Bluesky checks reported"},
    "blueskyweb.xyz":{"status": "yes",    "note": "Bluesky infra domain (conservative)"},
    "tiktok.com":   {"status": "unknown", "note": "Mixed reports; treat as unknown"},
    "instagram.com":{"status": "unknown", "note": "Mixed reports; treat as unknown"},
    "facebook.com": {"status": "unknown", "note": "Mixed reports; treat as unknown"},
    "snapchat.com": {"status": "unknown", "note": "Mixed reports; treat as unknown"},

    # Dating / Adult
    "grindr.com":   {"status": "yes",     "note": "Explicit age checks reported in UK"},
    "pornhub.com":  {"status": "yes",     "note": "Age verification enforced in UK"},
    "onlyfans.com": {"status": "unknown", "note": "Likely checks; verify"},
    "xvideos.com":  {"status": "unknown", "note": "Likely checks; verify"},
    "xnxx.com":     {"status": "unknown", "note": "Likely checks; verify"},
    "xhamster.com": {"status": "unknown", "note": "Likely checks; verify"},

    # Messaging
    "telegram.org": {"status": "unknown", "note": "Unclear; treat as unknown"},
    "whatsapp.com": {"status": "unknown", "note": "Unclear; treat as unknown"},

    # Gaming / Misc
    "steamcommunity.com": {"status": "unknown", "note": None},
    "store.steampowered.com": {"status": "unknown", "note": None},
}


def get_status(domain: str) -> dict[str, str | None]:
    """
    Lookup helper. Returns a dict {status, note}.
    Defaults to {"status": "unknown", "note": None} if not found.
    """
    d = domain.lower()
    # Exact match first
    if d in CURATED:
        return CURATED[d]
    # Fallback: strip common 'www.' prefix
    if d.startswith("www.") and d[4:] in CURATED:
        return CURATED[d[4:]]
    return {"status": "unknown", "note": None}
