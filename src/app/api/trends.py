from __future__ import annotations

import asyncio
import io
from functools import lru_cache
from typing import Optional

from flask import Blueprint, jsonify, request, send_file

bp = Blueprint("api_trends", __name__)


def _param(name: str, default: str) -> str:
    v = request.args.get(name)
    return v if v else default


@lru_cache(maxsize=64)
def _cache_key(q: str, geo: str, time: str) -> str:  # noqa: ARG001 (used by lru_cache)
    return f"{q}|{geo}|{time}"


async def _screenshot_trends_png_async(q: str, geo: str, time: str) -> bytes:
    # Lazy import to avoid heavy startup cost when not used
    from pyppeteer import launch  # type: ignore

    url = (
        "https://trends.google.com/trends/explore?"
        f"date={time}&geo={geo}&q={q}&hl=en"
    )

    browser = await launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--window-size=1280,720",
        ],
    )
    try:
        page = await browser.newPage()
        await page.setViewport({"width": 1280, "height": 720, "deviceScaleFactor": 2})
        await page.goto(url, {"waitUntil": "networkidle2", "timeout": 60000})
        await asyncio.sleep(3)
        png = await page.screenshot(fullPage=True)
        return png  # type: ignore[return-value]
    finally:
        await browser.close()


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@bp.get("/trends/png")
def trends_png():
    """
    GET /api/trends/png?q=vpn&geo=GB&time=today%2012-m

    Best-effort PNG screenshot of Google Trends explore page to avoid client-side
    embed quota issues (429). This uses a headless browser. It may still be
    rate-limited by Google depending on IP.
    """
    q = _param("q", "vpn")
    geo = _param("geo", "GB")
    time = _param("time", "today 12-m")

    try:
        png_bytes: bytes = _run(_screenshot_trends_png_async(q, geo, time))
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 502

    return send_file(io.BytesIO(png_bytes), mimetype="image/png")
