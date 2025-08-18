from __future__ import annotations
from typing import Dict, List, Optional
from flask import Blueprint, jsonify, request

from app.analytics.joiners import _latest_date_for_country
from app.db.mongo import get_collection
from app.data.age_gate_curated import CURATED, get_status

bp = Blueprint("api_age_gate", __name__)


def _resolved_date(country: str, date: Optional[str]) -> Optional[str]:
	return date or _latest_date_for_country(country)


@bp.get("/age-gate/status")
def age_gate_status():
	"""
	GET /api/age-gate/status?country=GB&date=YYYY-MM-DD&limit=10
	Returns curated age-gate statuses and flags whether any are in the day's Top-N.
	"""
	country = request.args.get("country", "GB").upper()
	date = request.args.get("date")
	limit = int(request.args.get("limit", 10))

	day = _resolved_date(country, date)
	top_map: Dict[str, int] = {}
	if day:
		cur = (
			get_collection("domain_rank")
			.find({"country": country, "date": day}, {"_id": 0, "domain": 1, "rank": 1})
			.sort("rank", 1)
			.limit(limit)
		)
		for doc in cur:
			top_map[doc["domain"].lower()] = int(doc["rank"])

	results: List[Dict] = []
	for domain in sorted(CURATED.keys()):
		status = get_status(domain)
		dlow = domain.lower()
		in_top = dlow in top_map
		results.append(
			{
				"domain": domain,
				"status": status.get("status", "unknown"),
				"note": status.get("note"),
				"in_top": in_top,
				"rank": top_map.get(dlow),
			}
		)

	return jsonify(
		{
			"ok": True,
			"country": country,
			"date": day,
			"limit": limit,
			"results": results,
			"counts": {
				"yes": sum(1 for r in results if r["status"] == "yes"),
				"unknown": sum(1 for r in results if r["status"] == "unknown"),
				"no": sum(1 for r in results if r["status"] == "no"),
				"in_top": sum(1 for r in results if r["in_top"]),
			},
		}
	)


@bp.get("/age-gate/timeseries")
def age_gate_timeseries():
	"""
	GET /api/age-gate/timeseries?country=GB&since=YYYY-MM-DD&limit=100
	Returns daily count of Top-N domains that are age-gated from a specific date onwards.
	"""
	country = request.args.get("country", "GB").upper()
	since = request.args.get("since", "2025-07-24")  # Default to July 24
	limit = int(request.args.get("limit", 100))

	coll = get_collection("domain_rank")
	all_dates = sorted(coll.distinct("date", {"country": country}))
	
	# Filter dates from July 24 onwards
	filtered_dates = [d for d in all_dates if d >= since]

	points: List[Dict] = []
	for d in filtered_dates:
		top = list(
			coll.find({"country": country, "date": d}, {"_id": 0, "domain": 1, "rank": 1})
			.sort("rank", 1)
			.limit(limit)
		)
		if not top:
			continue
		gated = 0
		for doc in top:
			status = get_status(doc["domain"]).get("status", "unknown")
			if status == "yes":
				gated += 1
		# Return count instead of percentage
		points.append({"ts": f"{d}T00:00:00Z", "value": gated})

	return jsonify({"ok": True, "country": country, "since": since, "limit": limit, "points": points})
