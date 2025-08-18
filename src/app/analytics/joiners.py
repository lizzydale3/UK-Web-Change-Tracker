from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from app.db.mongo import get_collection
from app.data.age_gate_curated import get_status as age_gate_status


def _latest_date_for_country(country: str) -> Optional[str]:
    """
    Return the most recent 'date' present in domain_rank for the given country.
    Dates are stored as YYYY-MM-DD strings; lexicographic sort is fine.
    """
    coll = get_collection("domain_rank")
    doc = coll.find({"country": country.upper()}, {"_id": 0, "date": 1}).sort("date", -1).limit(1)
    rows = list(doc)
    return rows[0]["date"] if rows else None


def top_domains_for_day(
    country: str,
    date: Optional[str] = None,
    limit: int = 10,
    category: Optional[str] = None,
) -> Tuple[Optional[str], List[Dict]]:
    """
    Load the top domains for a given country/day (or latest day if date is None).
    Returns (resolved_date, rows[{country,date,domain,rank,category}]).
    """
    country = country.upper()
    coll = get_collection("domain_rank")

    day = date or _latest_date_for_country(country)
    if not day:
        return None, []

    q: Dict = {"country": country, "date": day}
    if category:
        q["category"] = category

    cur = coll.find(q, {"_id": 0}).sort("rank", 1).limit(int(limit))
    return day, list(cur)


def top_domains_with_age_gate(
    country: str,
    date: Optional[str] = None,
    limit: int = 10,
    category: Optional[str] = None,
) -> Dict:
    """
    Fetch top domains and annotate each with curated age-gate status.
    Returns:
      {
        "country": "GB",
        "date": "YYYY-MM-DD" | None,
        "results": [{...domain doc..., "age_gate": {"status": "...", "note": "..."}}, ...],
        "counts": {"yes": n, "unknown": n, "no": n}
      }
    """
    day, rows = top_domains_for_day(country=country, date=date, limit=limit, category=category)
    counts = {"yes": 0, "unknown": 0, "no": 0}
    out: List[Dict] = []

    for r in rows:
        domain = r.get("domain", "")
        ag = age_gate_status(domain)
        status = (ag.get("status") or "unknown").lower()
        if status not in counts:
            status = "unknown"
        counts[status] += 1
        out.append({**r, "age_gate": {"status": status, "note": ag.get("note")}})

    return {
        "country": country.upper(),
        "date": day,
        "results": out,
        "counts": counts,
    }
