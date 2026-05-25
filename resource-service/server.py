import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("resource-service")

# Always serve the latest portal.html from GitHub main so updates flow without
# rebuilding this container (same "push, no rebuild" pattern as radio/console).
PORTAL_URL = os.getenv(
    "PORTAL_URL",
    "https://raw.githubusercontent.com/Jdoink/sovereignty_stack/main/command-center-portal/portal.html",
)
THEATER_URL = os.getenv(
    "THEATER_URL",
    "https://raw.githubusercontent.com/Jdoink/sovereignty_stack/main/command-center-portal/theater.html",
)

http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
    logger.info("HTTP client initialized")
    try:
        yield
    finally:
        if http_client is not None:
            await http_client.aclose()
        logger.info("HTTP client closed")


app = FastAPI(
    title="Sovereignty Stack Resource Service",
    description="Serves the Sovereign Resource Portal (and, later, the vault API + Media Theater).",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/portal", status_code=302)


async def _serve_page(url: str, label: str) -> HTMLResponse:
    """Serve the latest page HTML from GitHub main; fall back to a small notice
    page if GitHub is unreachable."""
    if http_client is not None:
        try:
            r = await http_client.get(url)
            if r.status_code == 200 and r.text:
                return HTMLResponse(
                    content=r.text,
                    headers={"Cache-Control": "no-store, max-age=0"},
                )
        except Exception:
            logger.exception("failed to fetch %s from %s", label, url)

    fallback = (
        "<!doctype html><meta charset='utf-8'>"
        f"<title>{label}</title>"
        "<body style='font-family:system-ui;background:#050816;color:#edfdf8;"
        "padding:24px'>"
        f"<h2 style='color:#86efac'>{label} unavailable</h2>"
        f"<p>Could not fetch the page from <code>{url}</code>.</p>"
        "<p>Check the Pi's network connection and try again.</p>"
        "</body>"
    )
    return HTMLResponse(content=fallback, status_code=503)


@app.get("/portal", response_class=HTMLResponse, include_in_schema=False)
async def portal() -> HTMLResponse:
    return await _serve_page(PORTAL_URL, "Sovereign Resource Portal")


@app.get("/theater", response_class=HTMLResponse, include_in_schema=False)
async def theater() -> HTMLResponse:
    return await _serve_page(THEATER_URL, "Media Theater")
