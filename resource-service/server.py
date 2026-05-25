import hashlib
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

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
VAULT_PAGE_URL = os.getenv(
    "VAULT_PAGE_URL",
    "https://raw.githubusercontent.com/Jdoink/sovereignty_stack/main/command-center-portal/vault.html",
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
    return RedirectResponse(url="/vault", status_code=302)


@app.get("/vault", response_class=HTMLResponse, include_in_schema=False)
async def vault_page() -> HTMLResponse:
    return await _serve_page(VAULT_PAGE_URL, "The Vault")


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


# === Resource Vault =========================================================
# A flat JSON array of saved resources (links + media), stored on the Seagate
# (mounted as /data) so it survives container rebuilds and syncs across every
# device on the LAN/tailnet. Same persistence pattern as the radio library.
VAULT_PATH = Path(os.getenv("RESOURCE_DATA_PATH", "/data")) / "vault.json"
MAX_ITEMS = 2000
VALID_TYPES = {"link", "media-archive", "media-direct"}
VALID_MEDIA = {"video", "audio"}

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
}


def _read_vault() -> List[Dict[str, Any]]:
    try:
        if VAULT_PATH.exists():
            data = json.loads(VAULT_PATH.read_text())
            if isinstance(data, list):
                return data
    except Exception:
        logger.exception("failed to read vault at %s", VAULT_PATH)
    return []


def _write_vault(items: List[Dict[str, Any]]) -> None:
    VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = VAULT_PATH.with_suffix(VAULT_PATH.suffix + ".tmp")
    tmp.write_text(json.dumps(items, indent=2))
    tmp.replace(VAULT_PATH)


def _s(raw: Any, limit: int) -> str:
    return str(raw if raw is not None else "").strip()[:limit]


def _normalize(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Validate + normalize an incoming item. The id is derived from the
    identifier (archive.org) or URL so the same resource can't be saved twice."""
    if not isinstance(raw, dict):
        raise ValueError("item must be an object")
    url = _s(raw.get("url"), 1000)
    identifier = _s(raw.get("identifier"), 200)
    if not url and not identifier:
        raise ValueError("url or identifier is required")
    key = (identifier or url).lower()
    name = _s(raw.get("name"), 200) or identifier or url
    item_type = raw.get("type") if raw.get("type") in VALID_TYPES else "link"
    media = raw.get("media") if raw.get("media") in VALID_MEDIA else None
    return {
        "id": hashlib.sha1(key.encode("utf-8")).hexdigest()[:16],
        "name": name,
        "url": url,
        "identifier": identifier,
        "category": _s(raw.get("category"), 80) or "Saved",
        "type": item_type,
        "media": media,
        "tag": _s(raw.get("tag"), 24),
        "desc": _s(raw.get("desc"), 300),
        "thumb": _s(raw.get("thumb"), 1000),
        "source": _s(raw.get("source"), 24) or "manual",
        "notes": _s(raw.get("notes"), 1000),
        "added_at": int(time.time()),
    }


@app.get("/api/vault")
async def get_vault() -> JSONResponse:
    return JSONResponse(content=_read_vault(), headers=CORS_HEADERS)


@app.post("/api/vault")
async def add_to_vault(raw: Any = Body(...)) -> JSONResponse:
    try:
        item = _normalize(raw)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    items = _read_vault()
    for existing in items:
        if existing.get("id") == item["id"]:
            return JSONResponse(
                content={"ok": True, "duplicate": True, "item": existing, "count": len(items)},
                headers=CORS_HEADERS,
            )
    if len(items) >= MAX_ITEMS:
        raise HTTPException(status_code=409, detail=f"vault is full ({MAX_ITEMS} items)")
    items.append(item)
    _write_vault(items)
    return JSONResponse(
        content={"ok": True, "duplicate": False, "item": item, "count": len(items)},
        headers=CORS_HEADERS,
    )


@app.delete("/api/vault/{item_id}")
async def delete_from_vault(item_id: str) -> JSONResponse:
    items = _read_vault()
    kept = [it for it in items if it.get("id") != item_id]
    if len(kept) == len(items):
        raise HTTPException(status_code=404, detail="item not found")
    _write_vault(kept)
    return JSONResponse(content={"ok": True, "count": len(kept)}, headers=CORS_HEADERS)


@app.options("/api/vault")
@app.options("/api/vault/{item_id}")
async def vault_options(item_id: str = "") -> Response:
    return Response(headers=CORS_HEADERS)
