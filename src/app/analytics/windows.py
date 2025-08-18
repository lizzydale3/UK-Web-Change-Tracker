from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.db.mongo import get_collection


def _find_series(country: str, metric: str, since_iso: str, until_iso: str) -> List[Dict]:
    coll = get_collection("traffic_ts")
    q = {
        "country": country.upper(),
        "metric": metric,
        "ts": {"$gte": since_iso, "$lte": until_iso},
    }
    cur = coll.find(q, {"_id": 0, "ts": 1, "value": 1}).sort("ts", 1)
    return list(cur)


def _align_by_ts(series_list: List[List[Dict]]) -> Dict[str, List[Optional[float]]]:
    all_ts = sorted({pt["ts"] for s in series_list for pt in s})
    aligned: Dict[str, List[Optional[float]]] = {ts: [None] * len(series_list) for ts in all_ts}
    for idx, s in enumerate(series_list):
        kv = {pt["ts"]: pt["value"] for pt in s}
        for ts in all_ts:
            if ts in kv:
                aligned[ts][idx] = float(kv[ts])
    return aligned


def _mean(vals: List[float]) -> Optional[float]:
    if not vals:
        return None
    arr = np.array(vals, dtype=float)
    if arr.size == 0:
        return None
    return float(np.mean(arr))


def compute_window_stats(
    country: str,
    metric: str,
    event: str,          # "YYYY-MM-DD"
    pre_days: int = 14,
    post_days: int = 14,
    controls: Optional[List[str]] = None,
) -> Dict:
    """
    Core stat block used by /api/window-stats:
      - mean_pre, mean_post, pct_delta
      - z-score vs synthetic control (avg of controls)
    """
    controls = controls or []
    # Build windows in ISO (treat event as midnight, inclusive/exclusive like API did)
    event_dt = datetime.fromisoformat(event)
    pre_since = (event_dt - timedelta(days=pre_days)).isoformat()
    pre_until = (event_dt - timedelta(seconds=1)).isoformat()
    post_since = event_dt.isoformat()
    post_until = (event_dt + timedelta(days=post_days)).isoformat()

    s_pre = _find_series(country, metric, pre_since, pre_until)
    s_post = _find_series(country, metric, post_since, post_until)

    mean_pre = _mean([p["value"] for p in s_pre])
    mean_post = _mean([p["value"] for p in s_post])

    pct_delta = None
    if mean_pre and mean_pre != 0:
        pct_delta = float((mean_post - mean_pre) / mean_pre) if mean_post is not None else None

    z_score = None
    controls_detail: Dict[str, Dict[str, int]] = {}

    if controls:
        pre_series_list = [s_pre] + [_find_series(c, metric, pre_since, pre_until) for c in controls]
        post_series_list = [s_post] + [_find_series(c, metric, post_since, post_until) for c in controls]

        def _period_stats(series_list: List[List[Dict]]) -> Optional[Tuple[float, float]]:
            aligned = _align_by_ts(series_list)
            diffs = []
            for ts, vect in aligned.items():
                base = vect[0]
                ctrls = [v for v in vect[1:] if v is not None]
                if base is None or not ctrls:
                    continue
                ctrl_mean = float(np.mean(ctrls))
                diffs.append(base - ctrl_mean)
            if not diffs:
                return None
            return float(np.mean(diffs)), float(np.std(diffs) or 0.0)

        pre_res = _period_stats(pre_series_list)
        post_res = _period_stats(post_series_list)

        if pre_res and post_res:
            pre_mean_diff, pre_std = pre_res
            post_mean_diff, _ = post_res
            if pre_std and pre_std > 0:
                z_score = float((post_mean_diff - pre_mean_diff) / pre_std)

        for c in controls:
            controls_detail[c] = {
                "pre_points": len(_find_series(c, metric, pre_since, pre_until)),
                "post_points": len(_find_series(c, metric, post_since, post_until)),
            }

    return {
        "country": country.upper(),
        "metric": metric,
        "event": event,
        "pre_days": pre_days,
        "post_days": post_days,
        "mean_pre": mean_pre,
        "mean_post": mean_post,
        "pct_delta": pct_delta,
        "z_score_vs_controls": z_score,
        "controls": controls,
        "controls_detail": controls_detail,
    }
