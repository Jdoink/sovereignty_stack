import base64
import hashlib
import json
import logging
import os
import re
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import markdown as md
import yaml
from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

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
STUDIO_URL = os.getenv(
    "STUDIO_URL",
    "https://raw.githubusercontent.com/Jdoink/sovereignty_stack/main/command-center-portal/studio.html",
)
ENTRANCE_URL = os.getenv(
    "ENTRANCE_URL",
    "https://raw.githubusercontent.com/Jdoink/sovereignty_stack/main/command-center-portal/entrance.html",
)
LIBRARY_URL = os.getenv(
    "LIBRARY_URL",
    "https://raw.githubusercontent.com/Jdoink/sovereignty_stack/main/command-center-portal/library.html",
)

http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
    logger.info("HTTP client initialized")
    try:
        library_startup()
        await _seed_fetch_assets()
    except Exception:
        logger.exception("library startup failed")
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

# Self-hosted classical fonts (Cinzel / Cormorant) for the Vault. The dir is
# committed (with a README) so it always exists; until the font files are
# dropped in, the pages fall back to a web-safe classical stack.
FONTS_DIR = Path(__file__).resolve().parent / "fonts"
FONTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/fonts", StaticFiles(directory=str(FONTS_DIR)), name="fonts")


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


@app.get("/studio", response_class=HTMLResponse, include_in_schema=False)
async def studio() -> HTMLResponse:
    return await _serve_page(STUDIO_URL, "Art Studio")


@app.get("/entrance", response_class=HTMLResponse, include_in_schema=False)
async def entrance() -> HTMLResponse:
    return await _serve_page(ENTRANCE_URL, "Enter The Vault")


@app.get("/library", response_class=HTMLResponse, include_in_schema=False)
async def library_page() -> HTMLResponse:
    return await _serve_page(LIBRARY_URL, "The Library")


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


# === Art Studio gallery =====================================================
# Paintings are stored as PNG files on the Seagate (RESOURCE_DATA_PATH/art),
# with an index.json of {id, name, created} — open formats, recoverable,
# and the seed of the Family Archive (e.g. the kids' artwork).
ART_DIR = Path(os.getenv("RESOURCE_DATA_PATH", "/data")) / "art"
ART_DIR.mkdir(parents=True, exist_ok=True)
ART_INDEX = ART_DIR / "index.json"
MAX_ART = 1000
MAX_ART_BYTES = 8 * 1024 * 1024  # 8 MB per painting
_ID_RE = re.compile(r"^[a-f0-9]{8,32}$")

app.mount("/art", StaticFiles(directory=str(ART_DIR)), name="art")


def _read_art_index() -> List[Dict[str, Any]]:
    try:
        if ART_INDEX.exists():
            data = json.loads(ART_INDEX.read_text())
            if isinstance(data, list):
                return data
    except Exception:
        logger.exception("failed to read art index")
    return []


def _write_art_index(items: List[Dict[str, Any]]) -> None:
    tmp = ART_INDEX.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(items, indent=2))
    tmp.replace(ART_INDEX)


@app.get("/api/art")
async def list_art() -> JSONResponse:
    return JSONResponse(content=_read_art_index(), headers=CORS_HEADERS)


@app.post("/api/art")
async def save_art(payload: Any = Body(...)) -> JSONResponse:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="body must be an object")
    name = str(payload.get("name", "Untitled")).strip()[:60] or "Untitled"
    data_url = str(payload.get("dataUrl", ""))
    prefix = "data:image/png;base64,"
    if not data_url.startswith(prefix):
        raise HTTPException(status_code=400, detail="dataUrl must be a base64 PNG")
    try:
        raw = base64.b64decode(data_url[len(prefix):], validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid base64 image data")
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise HTTPException(status_code=400, detail="not a valid PNG")
    if len(raw) > MAX_ART_BYTES:
        raise HTTPException(status_code=413, detail="painting too large")
    index = _read_art_index()
    if len(index) >= MAX_ART:
        raise HTTPException(status_code=409, detail=f"gallery is full ({MAX_ART})")
    art_id = uuid.uuid4().hex[:16]
    (ART_DIR / (art_id + ".png")).write_bytes(raw)
    entry = {"id": art_id, "name": name, "created": int(time.time())}
    index.insert(0, entry)
    _write_art_index(index)
    return JSONResponse(content={"ok": True, "item": entry, "count": len(index)}, headers=CORS_HEADERS)


@app.delete("/api/art/{art_id}")
async def delete_art(art_id: str) -> JSONResponse:
    if not _ID_RE.match(art_id):
        raise HTTPException(status_code=400, detail="bad id")
    index = _read_art_index()
    kept = [it for it in index if it.get("id") != art_id]
    if len(kept) == len(index):
        raise HTTPException(status_code=404, detail="not found")
    try:
        (ART_DIR / (art_id + ".png")).unlink(missing_ok=True)
    except Exception:
        logger.exception("failed to delete art file %s", art_id)
    _write_art_index(kept)
    return JSONResponse(content={"ok": True, "count": len(kept)}, headers=CORS_HEADERS)


@app.options("/api/art")
@app.options("/api/art/{art_id}")
async def art_options(art_id: str = "") -> Response:
    return Response(headers=CORS_HEADERS)


# === The Library — knowledge substrate ======================================
# Files-as-truth: each entry is a Markdown file with YAML front-matter under
# /data/library/entries/<slug>.md; media + archived source snapshots live in
# /data/library/assets. A SQLite FTS5 index (index.db) is *derived* from the
# files and rebuilt on every write, so the files remain the durable, portable,
# human-readable source of truth (open formats, recoverable, editable anywhere).
LIB_DIR = Path(os.getenv("RESOURCE_DATA_PATH", "/data")) / "library"
ENTRIES_DIR = LIB_DIR / "entries"
ASSETS_DIR = LIB_DIR / "assets"
VERSIONS_DIR = LIB_DIR / ".versions"
INDEX_DB = LIB_DIR / "index.db"
ENTRIES_DIR.mkdir(parents=True, exist_ok=True)
(ASSETS_DIR / "sources").mkdir(parents=True, exist_ok=True)
app.mount("/library-assets", StaticFiles(directory=str(ASSETS_DIR)), name="library-assets")

STATUSES = {"seedling", "reviewed", "canonical"}
CONFIDENCE = {"unrated", "low", "medium", "high"}
# Tiers form a learning ladder within a domain; TIER_ORDER drives Path-view sorting.
TIER_ORDER = ["roadmap", "eli5", "intro", "deep-dive", "mastery", "resource", ""]
TIERS = set(TIER_ORDER)
SEED_DIR = Path(__file__).resolve().parent / "seed" / "library"
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _today() -> str:
    return date.today().isoformat()


def slugify(raw: Any) -> str:
    s = _SLUG_RE.sub("-", str(raw or "").strip().lower()).strip("-")
    return s[:80] or "untitled"


def _clean_list(raw: Any) -> List[str]:
    if isinstance(raw, str):
        raw = raw.split(",")
    if not isinstance(raw, list):
        return []
    seen, out = set(), []
    for x in raw:
        v = str(x).strip()[:60]
        if v and v.lower() not in seen:
            seen.add(v.lower())
            out.append(v)
    return out[:40]


def _clean_date(raw: Any) -> str:
    s = str(raw or "").strip()[:10]
    return s if re.match(r"^\d{4}-\d{2}-\d{2}$", s) else ""


def _clean_sources(raw: Any) -> List[Dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out = []
    for s in raw[:50]:
        if not isinstance(s, dict):
            continue
        url = _s(s.get("url"), 1000)
        title = _s(s.get("title"), 240) or url
        if not (url or title):
            continue
        item = {"title": title}
        if url:
            item["url"] = url
        for k, lim in (("author", 160), ("archived", 200), ("type", 24)):
            v = _s(s.get(k), lim)
            if v:
                item[k] = v
        item["retrieved"] = _clean_date(s.get("retrieved")) or _today()
        out.append(item)
    return out


def _normalize_entry(raw: Dict[str, Any], existing: Optional[Dict[str, Any]] = None):
    if not isinstance(raw, dict):
        raise ValueError("entry must be an object")
    title = _s(raw.get("title"), 240)
    if not title:
        raise ValueError("title is required")
    status = raw.get("status") if raw.get("status") in STATUSES else "seedling"
    sources = _clean_sources(raw.get("sources"))
    if status == "canonical" and not any(s.get("url") for s in sources):
        raise ValueError("a canonical entry needs at least one cited source")
    now = int(time.time())
    meta = {
        "title": title,
        "slug": slugify(raw.get("slug") or title),
        "domain": _s(raw.get("domain"), 80) or "Uncategorized",
        "topics": _clean_list(raw.get("topics")),
        "summary": _s(raw.get("summary"), 600),
        "status": status,
        "confidence": raw.get("confidence") if raw.get("confidence") in CONFIDENCE else "unrated",
        "tier": raw.get("tier") if raw.get("tier") in TIERS else "",
        "order": int(raw.get("order") or 0) if str(raw.get("order") or "0").lstrip("-").isdigit() else 0,
        "verified": _clean_date(raw.get("verified")),
        "sources": sources,
        "media": _clean_list(raw.get("media")),
        "related": _clean_list(raw.get("related")),
        "created": int((existing or {}).get("created") or now),
        "updated": now,
    }
    body = str(raw.get("body") or "").strip()
    return meta, body


def _stringify_dates(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _stringify_dates(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_stringify_dates(v) for v in obj]
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    return obj


def parse_entry(text: str):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            meta = yaml.safe_load(text[3:end]) or {}
            body = text[end + 4:].lstrip("\n")
            return (_stringify_dates(meta) if isinstance(meta, dict) else {}), body
    return {}, text


def dump_entry(meta: Dict[str, Any], body: str) -> str:
    fm = yaml.safe_dump(meta, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{fm}\n---\n\n{body.strip()}\n"


def _snapshot(p: Path) -> None:
    """Save the current contents of an entry file to .versions/<slug>/<ms>.md
    before it is overwritten or deleted, so every change is recoverable."""
    if not p.exists():
        return
    d = VERSIONS_DIR / p.stem
    d.mkdir(parents=True, exist_ok=True)
    (d / (str(int(time.time() * 1000)) + ".md")).write_bytes(p.read_bytes())


def _list_versions(slug: str) -> List[Dict[str, Any]]:
    d = VERSIONS_DIR / slug
    if not d.is_dir():
        return []
    out = []
    for f in d.glob("*.md"):
        try:
            ts = int(f.stem)
        except ValueError:
            continue
        out.append({"ts": ts, "when": datetime.fromtimestamp(ts / 1000).isoformat(timespec="minutes")})
    return sorted(out, key=lambda v: v["ts"], reverse=True)


def _write_entry(meta: Dict[str, Any], body: str) -> None:
    ENTRIES_DIR.mkdir(parents=True, exist_ok=True)
    p = ENTRIES_DIR / (meta["slug"] + ".md")
    _snapshot(p)
    tmp = p.with_suffix(".md.tmp")
    tmp.write_text(dump_entry(meta, body), encoding="utf-8")
    tmp.replace(p)


def read_all_metas(with_body: bool = False) -> List[Dict[str, Any]]:
    out = []
    for p in sorted(ENTRIES_DIR.glob("*.md")):
        try:
            meta, body = parse_entry(p.read_text(encoding="utf-8"))
        except Exception:
            logger.exception("failed to parse entry %s", p)
            continue
        if not isinstance(meta, dict):
            continue
        meta["slug"] = str(meta.get("slug") or p.stem)
        if with_body:
            meta["_body"] = body
        out.append(meta)
    return out


def _card(meta: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "title": meta.get("title", ""),
        "slug": meta.get("slug", ""),
        "domain": meta.get("domain", "Uncategorized"),
        "topics": meta.get("topics") or [],
        "summary": meta.get("summary", ""),
        "status": meta.get("status", "seedling"),
        "confidence": meta.get("confidence", "unrated"),
        "tier": meta.get("tier", ""),
        "order": meta.get("order", 0),
        "verified": meta.get("verified", ""),
        "updated": meta.get("updated", 0),
        "n_sources": len(meta.get("sources") or []),
        "n_media": len(meta.get("media") or []),
    }


def rebuild_index() -> None:
    metas = read_all_metas(with_body=True)
    con = sqlite3.connect(str(INDEX_DB))
    try:
        con.execute("DROP TABLE IF EXISTS libfts")
        con.execute("CREATE VIRTUAL TABLE libfts USING fts5(slug, title, summary, topics, body)")
        con.executemany(
            "INSERT INTO libfts(slug,title,summary,topics,body) VALUES(?,?,?,?,?)",
            [(m["slug"], m.get("title", ""), m.get("summary", ""),
              " ".join(m.get("topics") or []), m.get("_body", "")) for m in metas],
        )
        con.commit()
    finally:
        con.close()


def _fts_query(q: str) -> str:
    toks = re.findall(r"[A-Za-z0-9]+", q)
    return " ".join(t + "*" for t in toks)


def fts_search(q: str) -> Optional[List[str]]:
    expr = _fts_query(q)
    if not expr:
        return []
    try:
        con = sqlite3.connect(str(INDEX_DB))
        try:
            rows = con.execute(
                "SELECT slug FROM libfts WHERE libfts MATCH ? ORDER BY rank", (expr,)
            ).fetchall()
        finally:
            con.close()
        return [r[0] for r in rows]
    except Exception:
        logger.exception("library search failed")
        return None


def _seed_from_files() -> None:
    """Materialize bundled curriculum onto the Seagate. Entries (Markdown +
    front-matter) and assets (diagrams, etc.) ship in the repo under seed/library
    and are copied to /data only when absent — so authored content arrives once
    and the user's own edits are never overwritten."""
    se = SEED_DIR / "entries"
    if se.is_dir():
        for p in sorted(se.glob("*.md")):
            dest = ENTRIES_DIR / p.name
            if not dest.exists():
                dest.write_bytes(p.read_bytes())
                logger.info("seeded entry %s", p.name)
    sa = SEED_DIR / "assets"
    if sa.is_dir():
        for p in sa.rglob("*"):
            if p.is_file():
                dest = ASSETS_DIR / p.relative_to(sa)
                if not dest.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(p.read_bytes())


async def _seed_fetch_assets() -> None:
    """Hybrid-media: download open texts/PDFs listed in seed/library/fetch.json
    into the assets folder once, so they live on the drive (best-effort)."""
    manifest = SEED_DIR / "fetch.json"
    if not (manifest.is_file() and http_client is not None):
        return
    try:
        items = json.loads(manifest.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("could not read seed fetch manifest")
        return
    for it in items if isinstance(items, list) else []:
        url, rel = str(it.get("url", "")), str(it.get("path", ""))
        if not (re.match(r"^https?://", url) and rel):
            continue
        dest = (ASSETS_DIR / rel).resolve()
        if not str(dest).startswith(str(ASSETS_DIR.resolve())) or dest.exists():
            continue
        try:
            r = await http_client.get(url, follow_redirects=True)
            r.raise_for_status()
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(r.content[:60_000_000])
            logger.info("fetched seed asset %s", rel)
        except Exception:
            logger.exception("failed to fetch seed asset %s", url)


def library_startup() -> None:
    ENTRIES_DIR.mkdir(parents=True, exist_ok=True)
    (ASSETS_DIR / "sources").mkdir(parents=True, exist_ok=True)
    VERSIONS_DIR.mkdir(parents=True, exist_ok=True)
    _seed_from_files()
    rebuild_index()


@app.get("/api/library/domains")
async def library_domains() -> JSONResponse:
    counts: Dict[str, int] = {}
    for m in read_all_metas():
        d = m.get("domain") or "Uncategorized"
        counts[d] = counts.get(d, 0) + 1
    items = [{"domain": d, "count": c} for d, c in sorted(counts.items())]
    return JSONResponse(content=items, headers=CORS_HEADERS)


@app.get("/api/library/path/{domain}")
async def library_path(domain: str) -> JSONResponse:
    metas = [m for m in read_all_metas() if (m.get("domain") or "Uncategorized") == domain]
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for m in metas:
        t = m.get("tier") if m.get("tier") in TIERS else ""
        groups.setdefault(t, []).append(m)
    tiers = []
    for t in TIER_ORDER:
        items = sorted(groups.get(t, []), key=lambda m: (int(m.get("order") or 0), m.get("title", "")))
        if items:
            tiers.append({"tier": t, "items": [_card(m) for m in items]})
    return JSONResponse(content={"domain": domain, "tiers": tiers}, headers=CORS_HEADERS)


@app.get("/api/library/entries")
async def library_entries(domain: str = "", topic: str = "", status: str = "", q: str = "") -> JSONResponse:
    metas = read_all_metas()
    q = q.strip()
    if q:
        ranked = fts_search(q)
        if ranked is not None:
            order = {s: i for i, s in enumerate(ranked)}
            metas = [m for m in metas if m["slug"] in order]
            metas.sort(key=lambda m: order.get(m["slug"], 1_000_000))
        else:
            ql = q.lower()
            metas = [m for m in metas if ql in (m.get("title", "") + " " + m.get("summary", "")).lower()]
    if domain:
        metas = [m for m in metas if m.get("domain") == domain]
    if status:
        metas = [m for m in metas if m.get("status") == status]
    if topic:
        metas = [m for m in metas if topic in (m.get("topics") or [])]
    return JSONResponse(content=[_card(m) for m in metas], headers=CORS_HEADERS)


@app.get("/api/library/entries/{slug}")
async def library_entry(slug: str) -> JSONResponse:
    p = ENTRIES_DIR / (slugify(slug) + ".md")
    if not p.exists():
        raise HTTPException(status_code=404, detail="entry not found")
    meta, body = parse_entry(p.read_text(encoding="utf-8"))
    meta["slug"] = str(meta.get("slug") or p.stem)
    html = md.markdown(body, extensions=["extra", "sane_lists", "toc"])
    return JSONResponse(content={**meta, "body": body, "html": html}, headers=CORS_HEADERS)


@app.post("/api/library/entries")
async def library_save(raw: Any = Body(...)) -> JSONResponse:
    if not isinstance(raw, dict):
        raise HTTPException(status_code=400, detail="body must be an object")
    existing = None
    slug_in = slugify(raw.get("slug") or raw.get("title") or "")
    ep = ENTRIES_DIR / (slug_in + ".md")
    if ep.exists():
        em, _ = parse_entry(ep.read_text(encoding="utf-8"))
        existing = em if isinstance(em, dict) else None
    try:
        meta, body = _normalize_entry(raw, existing)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    _write_entry(meta, body)
    rebuild_index()
    return JSONResponse(
        content={"ok": True, "duplicate": existing is not None, "item": _card(meta)},
        headers=CORS_HEADERS,
    )


@app.delete("/api/library/entries/{slug}")
async def library_delete(slug: str) -> JSONResponse:
    p = ENTRIES_DIR / (slugify(slug) + ".md")
    if not p.exists():
        raise HTTPException(status_code=404, detail="entry not found")
    _snapshot(p)
    p.unlink()
    rebuild_index()
    return JSONResponse(content={"ok": True}, headers=CORS_HEADERS)


@app.get("/api/library/entries/{slug}/versions")
async def library_versions(slug: str) -> JSONResponse:
    return JSONResponse(content=_list_versions(slugify(slug)), headers=CORS_HEADERS)


@app.post("/api/library/entries/{slug}/restore")
async def library_restore(slug: str, raw: Any = Body(...)) -> JSONResponse:
    slug = slugify(slug)
    ts = (raw or {}).get("ts") if isinstance(raw, dict) else None
    vp = VERSIONS_DIR / slug / (str(ts) + ".md")
    if not vp.exists():
        raise HTTPException(status_code=404, detail="version not found")
    p = ENTRIES_DIR / (slug + ".md")
    _snapshot(p)  # restoring is itself undoable
    ENTRIES_DIR.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".md.tmp")
    tmp.write_bytes(vp.read_bytes())
    tmp.replace(p)
    rebuild_index()
    meta, _ = parse_entry(p.read_text(encoding="utf-8"))
    meta["slug"] = slug
    return JSONResponse(content={"ok": True, "item": _card(meta)}, headers=CORS_HEADERS)


@app.post("/api/library/preview")
async def library_preview(raw: Any = Body(...)) -> JSONResponse:
    body = str((raw or {}).get("body") or "") if isinstance(raw, dict) else ""
    html = md.markdown(body, extensions=["extra", "sane_lists", "toc"])
    return JSONResponse(content={"html": html}, headers=CORS_HEADERS)


@app.post("/api/library/clip")
async def library_clip(raw: Any = Body(...)) -> JSONResponse:
    """Save a web source: archive a local HTML snapshot (so the citation outlives
    link rot) and create a seedling reference entry. Single-user LAN tool; only
    http(s) URLs are fetched, and the snapshot is size-capped."""
    if not isinstance(raw, dict):
        raise HTTPException(status_code=400, detail="body must be an object")
    url = _s(raw.get("url"), 1000)
    if not re.match(r"^https?://", url):
        raise HTTPException(status_code=400, detail="a valid http(s) url is required")
    title = _s(raw.get("title"), 240)
    archived = ""
    if http_client is not None:
        try:
            r = await http_client.get(url, follow_redirects=True)
            text = r.text[:2_000_000]
            sha = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
            (ASSETS_DIR / "sources").mkdir(parents=True, exist_ok=True)
            (ASSETS_DIR / "sources" / (sha + ".html")).write_bytes(text.encode("utf-8", "ignore"))
            archived = f"sources/{sha}.html"
            if not title:
                m = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
                if m:
                    title = re.sub(r"\s+", " ", m.group(1)).strip()[:240]
        except Exception:
            logger.exception("clip fetch failed for %s", url)
    if not title:
        title = url
    note = _s(raw.get("note"), 2000)
    src: Dict[str, str] = {"title": title, "url": url, "type": "article", "retrieved": _today()}
    if archived:
        src["archived"] = archived
    payload = {
        "title": title,
        "domain": _s(raw.get("domain"), 80) or "References",
        "topics": raw.get("topics"),
        "summary": note[:300],
        "body": note,
        "status": "seedling",
        "sources": [src],
    }
    meta, body = _normalize_entry(payload)
    _write_entry(meta, body)
    rebuild_index()
    return JSONResponse(
        content={"ok": True, "item": _card(meta), "archived": bool(archived)},
        headers=CORS_HEADERS,
    )


@app.options("/api/library/{rest:path}")
async def library_options(rest: str = "") -> Response:
    return Response(headers=CORS_HEADERS)
