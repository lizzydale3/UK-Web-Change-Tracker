from __future__ import annotations

import asyncio
import io
import logging
from functools import lru_cache
from typing import Optional

from flask import Blueprint, jsonify, request, send_file

bp = Blueprint("api_trends", __name__)

# Set up logging
logger = logging.getLogger(__name__)


def _param(name: str, default: str) -> str:
    v = request.args.get(name)
    return v if v else default


@lru_cache(maxsize=64)
def _cache_key(q: str, geo: str, time: str) -> str:  # noqa: ARG001 (used by lru_cache)
    return f"{q}|{geo}|{time}"


async def _screenshot_trends_png_async(q: str, geo: str, time: str) -> bytes:
    # Lazy import to avoid heavy startup cost when not used
    try:
        from pyppeteer import launch  # type: ignore
    except ImportError as e:
        logger.error(f"pyppeteer not available: {e}")
        raise RuntimeError("Screenshot service not available - pyppeteer missing")

    url = (
        "https://trends.google.com/trends/explore?"
        f"date={time}&geo={geo}&q={q}&hl=en"
    )
    
    logger.info(f"Taking screenshot of Google Trends: {url}")
    
    browser = None
    try:
        browser = await launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=1280,720",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
            ],
        )
        
        page = await browser.newPage()
        await page.setViewport({"width": 1280, "height": 720, "deviceScaleFactor": 2})
        
        # Set user agent to avoid bot detection
        await page.setUserAgent(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Navigate to the page
        await page.goto(url, {"waitUntil": "networkidle2", "timeout": 30000})
        
        # Wait for content to load
        await asyncio.sleep(5)
        
        # Try to wait for specific elements that indicate the page is ready
        try:
            await page.waitForSelector('div[data-chart-type="TIMESERIES"]', timeout=10000)
        except Exception:
            logger.warning("TIMESERIES chart element not found, proceeding anyway")
        
        # Take screenshot
        png = await page.screenshot(fullPage=True)
        logger.info(f"Successfully captured screenshot for {q} in {geo}")
        return png  # type: ignore[return-value]
        
    except Exception as e:
        logger.error(f"Error taking screenshot: {e}")
        raise RuntimeError(f"Screenshot failed: {str(e)}")
    finally:
        if browser:
            try:
                await browser.close()
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@bp.get("/trends/health")
def trends_health():
    """
    GET /api/trends/health
    
    Check if the trends service is working properly
    """
    try:
        # Check if pyppeteer is available
        from pyppeteer import launch  # type: ignore
        return jsonify({
            "ok": True,
            "service": "trends",
            "status": "available",
            "message": "Trends service is ready"
        })
    except ImportError:
        return jsonify({
            "ok": False,
            "service": "trends", 
            "status": "unavailable",
            "error": "pyppeteer not installed",
            "message": "Install pyppeteer to enable screenshot functionality"
        }), 503
    except Exception as e:
        return jsonify({
            "ok": False,
            "service": "trends",
            "status": "error", 
            "error": str(e),
            "message": "Trends service encountered an error"
        }), 500


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

    logger.info(f"Trends PNG request: q={q}, geo={geo}, time={time}")

    try:
        png_bytes: bytes = _run(_screenshot_trends_png_async(q, geo, time))
        return send_file(io.BytesIO(png_bytes), mimetype="image/png")
    except Exception as e:
        logger.error(f"Trends PNG generation failed: {e}")
        return jsonify({
            "ok": False, 
            "error": str(e),
            "message": "Unable to generate screenshot. Try the direct link instead."
        }), 502
