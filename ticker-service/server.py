import asyncio
import html
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv
from fastapi import Body, FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("ticker-service")

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "").strip()

COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=bitcoin,ethereum,chainlink,aave,curve-dao-token"
    "&vs_currencies=usd&include_24hr_change=true&include_last_updated_at=true"
)
ETHERSCAN_URL = "https://api.etherscan.io/v2/api"
DEFILLAMA_PROTOCOLS = {
    "Aave": "https://api.llama.fi/protocol/aave",
    "Curve": "https://api.llama.fi/protocol/curve-dex",
}

cache: Dict[str, Tuple[float, Any]] = {}
http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global http_client
    timeout = httpx.Timeout(10.0)
    http_client = httpx.AsyncClient(timeout=timeout)
    logger.info("HTTP client initialized")
    try:
        yield
    finally:
        if http_client is not None:
            await http_client.aclose()
        logger.info("HTTP client closed")


app = FastAPI(title="Sovereignty Stack Ticker Service", lifespan=lifespan)


# === Radio library persistence ==============================================
# Library is just a JSON array of { name, sub, identifier, user }.
# Stored on the host's Seagate (mounted as /data via docker-compose volume)
# so it survives container rebuilds and syncs across every device that hits
# the same Pi.
RADIO_LIBRARY_PATH = Path(os.getenv("RADIO_LIBRARY_PATH", "/data/radio-library.json"))

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
}


def _read_radio_library() -> List[Dict[str, Any]]:
    try:
        if RADIO_LIBRARY_PATH.exists():
            data = json.loads(RADIO_LIBRARY_PATH.read_text())
            if isinstance(data, list):
                return data
    except Exception:
        logger.exception("Failed to read radio library at %s", RADIO_LIBRARY_PATH)
    return []


def _write_radio_library(items: List[Dict[str, Any]]) -> None:
    try:
        RADIO_LIBRARY_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp = RADIO_LIBRARY_PATH.with_suffix(RADIO_LIBRARY_PATH.suffix + ".tmp")
        tmp.write_text(json.dumps(items, indent=2))
        tmp.replace(RADIO_LIBRARY_PATH)
    except Exception:
        logger.exception("Failed to write radio library at %s", RADIO_LIBRARY_PATH)
        raise


@app.get("/radio-library")
async def get_radio_library() -> JSONResponse:
    return JSONResponse(content=_read_radio_library(), headers=CORS_HEADERS)


@app.post("/radio-library")
async def post_radio_library(items: Any = Body(...)) -> JSONResponse:
    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="body must be a JSON array")
    # Normalize: keep only objects with an identifier
    clean = [
        {
            "name": str(item.get("name", "UNKNOWN"))[:200],
            "sub": str(item.get("sub", ""))[:200],
            "identifier": str(item.get("identifier")),
            "user": True,
        }
        for item in items
        if isinstance(item, dict) and item.get("identifier")
    ]
    _write_radio_library(clean)
    return JSONResponse(
        content={"ok": True, "count": len(clean)},
        headers=CORS_HEADERS,
    )


@app.options("/radio-library")
async def options_radio_library() -> Response:
    return Response(headers=CORS_HEADERS)


async def fetch_json(url: str, params: Optional[Dict[str, str]] = None) -> Any:
    if http_client is None:
        raise RuntimeError("HTTP client not initialized")

    response = await http_client.get(url, params=params)
    response.raise_for_status()
    return response.json()


def get_cached(key: str) -> Optional[Any]:
    entry = cache.get(key)
    if not entry:
        return None

    expires_at, data = entry
    if time.time() >= expires_at:
        cache.pop(key, None)
        return None

    return data


def set_cached(key: str, data: Any, ttl_seconds: int) -> None:
    cache[key] = (time.time() + ttl_seconds, data)


def format_price(symbol: str, value: float) -> str:
    if symbol == "BTC":
        return f"${value / 1_000:,.1f}K"
    if symbol == "ETH":
        return f"${value / 1_000:,.2f}K"
    return f"${value:,.2f}"


def parse_tvl_value(payload: Dict[str, Any]) -> float:
    direct_tvl = payload.get("tvl")
    if isinstance(direct_tvl, (int, float)):
        return float(direct_tvl)
    if isinstance(direct_tvl, str):
        return float(direct_tvl.replace(",", ""))

    if isinstance(direct_tvl, list):
        for entry in reversed(direct_tvl):
            if isinstance(entry, (int, float)):
                return float(entry)
            if isinstance(entry, dict):
                for key in ["totalLiquidityUSD", "totalLiquidity", "tvl", "value"]:
                    value = entry.get(key)
                    if isinstance(value, (int, float)):
                        return float(value)
                    if isinstance(value, str):
                        try:
                            return float(value.replace(",", ""))
                        except ValueError:
                            continue

    current_chain_tvls = payload.get("currentChainTvls")
    if isinstance(current_chain_tvls, dict):
        total = 0.0
        found = False
        for value in current_chain_tvls.values():
            if isinstance(value, (int, float)):
                total += float(value)
                found = True
        if found:
            return total

    raise ValueError("Unable to parse TVL from DeFiLlama response")


def format_compact_usd(value: float) -> str:
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"${value / 1_000_000_000:,.1f}B"
    if abs_value >= 1_000_000:
        return f"${value / 1_000_000:,.2f}M"
    if abs_value >= 1_000:
        return f"${value / 1_000:,.2f}K"
    return f"${value:,.0f}"


async def get_coingecko_prices() -> Dict[str, float]:
    cache_key = "coingecko_prices"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    data = await fetch_json(COINGECKO_URL)
    prices = {
        "BTC": float(data["bitcoin"]["usd"]),
        "ETH": float(data["ethereum"]["usd"]),
        "LINK": float(data["chainlink"]["usd"]),
        "AAVE": float(data["aave"]["usd"]),
        "CRV": float(data["curve-dao-token"]["usd"]),
    }
    set_cached(cache_key, prices, ttl_seconds=60)
    return prices


async def get_eth_gas() -> Dict[str, str]:
    cache_key = "eth_gas"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    if not ETHERSCAN_API_KEY:
        raise ValueError("ETHERSCAN_API_KEY is missing")

    data = await fetch_json(
        ETHERSCAN_URL,
        params={
            "chainid": "1",
            "module": "gastracker",
            "action": "gasoracle",
            "apikey": ETHERSCAN_API_KEY,
        },
    )
    if str(data.get("status")) != "1" or "result" not in data:
        message = data.get("message", "unknown")
        result = data.get("result", "")
        raise ValueError(f"Etherscan API error: message={message}, result={result}")

    result = data["result"]
    gas = {
        "safe": str(result.get("SafeGasPrice", "?")),
        "standard": str(result.get("ProposeGasPrice", "?")),
        "fast": str(result.get("FastGasPrice", "?")),
    }
    set_cached(cache_key, gas, ttl_seconds=60)
    return gas


async def get_protocol_tvl(protocol_name: str, url: str) -> float:
    cache_key = f"defillama_tvl_{protocol_name.lower()}"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    payload = await fetch_json(url)
    tvl = parse_tvl_value(payload)
    set_cached(cache_key, tvl, ttl_seconds=600)
    return tvl


async def build_ticker_items() -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []

    prices_result, gas_result = await asyncio.gather(
        get_coingecko_prices(), get_eth_gas(), return_exceptions=True
    )

    if isinstance(prices_result, Exception):
        logger.exception("CoinGecko section failed", exc_info=prices_result)
        items.append({"text": "Warning: price data unavailable"})
    else:
        for symbol in ["BTC", "ETH", "LINK", "AAVE", "CRV"]:
            items.append({"text": f"{symbol} {format_price(symbol, prices_result[symbol])}"})

    if isinstance(gas_result, Exception):
        logger.exception("Etherscan gas section failed", exc_info=gas_result)
        items.append({"text": "Warning: ETH gas data unavailable"})
    else:
        items.append(
            {
                "text": (
                    f"ETH GAS Safe {gas_result['safe']} / "
                    f"Std {gas_result['standard']} / Fast {gas_result['fast']} gwei"
                )
            }
        )

    tvl_tasks = [get_protocol_tvl(name, url) for name, url in DEFILLAMA_PROTOCOLS.items()]
    tvl_results = await asyncio.gather(*tvl_tasks, return_exceptions=True)
    for (name, _), tvl_result in zip(DEFILLAMA_PROTOCOLS.items(), tvl_results):
        if isinstance(tvl_result, Exception):
            logger.exception("DeFiLlama TVL failed for %s", name, exc_info=tvl_result)
            items.append({"text": f"Warning: {name} TVL unavailable"})
        else:
            items.append({"text": f"{name} TVL {format_compact_usd(tvl_result)}"})

    return items


def items_to_line(items: List[Dict[str, str]]) -> str:
    return " | ".join(item.get("text", "") for item in items if item.get("text"))


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/ticker")
async def ticker() -> List[Dict[str, str]]:
    return await build_ticker_items()


@app.get("/ticker-line", response_class=PlainTextResponse)
async def ticker_line() -> str:
    items = await build_ticker_items()
    return items_to_line(items)


TICKER_CSS = """\
.ssticker-wrap {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 60px;
  overflow: hidden;
  background: transparent;
  display: flex;
  align-items: center;
}
.ssticker-track {
  display: inline-flex;
  white-space: nowrap;
  will-change: transform;
  animation: ssticker-scroll 22s linear infinite;
  color: #39ff7a;
  font-family: "SFMono-Regular", Menlo, Consolas, "Liberation Mono", monospace;
  font-weight: 600;
  font-size: clamp(20px, 10vh, 80px);
  letter-spacing: 0.025em;
  text-shadow:
    0 0 4px rgba(57, 255, 122, 0.7),
    0 0 12px rgba(57, 255, 122, 0.45),
    0 0 22px rgba(57, 255, 122, 0.25);
}
.ssticker-copy { padding-right: 4rem; }
@keyframes ssticker-scroll {
  from { transform: translate3d(0, 0, 0); }
  to   { transform: translate3d(-50%, 0, 0); }
}
"""


@app.get("/ticker.css")
async def ticker_css() -> Response:
    return Response(
        content=TICKER_CSS,
        media_type="text/css",
        headers={"Cache-Control": "public, max-age=300"},
    )


@app.get("/ticker-html", response_class=HTMLResponse)
async def ticker_html() -> HTMLResponse:
    items = await build_ticker_items()
    line = html.escape(items_to_line(items))

    content = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Sovereignty Ticker</title>
  <style>
    :root {{ color-scheme: dark; }}
    *, *::before, *::after {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      padding: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: transparent;
      color: #39ff7a;
      font-family: "SFMono-Regular", Menlo, Consolas, "Liberation Mono", monospace;
      font-weight: 600;
      letter-spacing: 0.025em;
    }}
    .ticker {{
      position: fixed;
      inset: 0;
      display: flex;
      align-items: center;
      overflow: hidden;
      background: transparent;
    }}
    .marquee {{
      display: inline-flex;
      flex: 0 0 auto;
      white-space: nowrap;
      will-change: transform;
      animation: ticker-scroll 22s linear infinite;
      font-size: clamp(22px, 10vh, 96px);
      line-height: 1;
      text-shadow: 0 0 6px rgba(57, 255, 122, 0.55);
    }}
    .copy {{ padding-right: 4rem; }}
    @keyframes ticker-scroll {{
      from {{ transform: translate3d(0, 0, 0); }}
      to   {{ transform: translate3d(-50%, 0, 0); }}
    }}
  </style>
</head>
<body>
  <div class="ticker" aria-label="Live ticker">
    <div class="marquee">
      <span class="copy" id="copy-a">{line}</span><span class="copy" id="copy-b">{line}</span>
    </div>
  </div>
  <script>
    (function() {{
      var a = document.getElementById('copy-a');
      var b = document.getElementById('copy-b');
      async function refresh() {{
        try {{
          var r = await fetch('/ticker-line', {{ cache: 'no-store' }});
          if (!r.ok) return;
          var text = await r.text();
          if (text && text !== a.textContent) {{
            a.textContent = text;
            b.textContent = text;
          }}
        }} catch (e) {{ /* network blip; try again next interval */ }}
      }}
      setInterval(refresh, 30000);
    }})();
  </script>
</body>
</html>"""

    return HTMLResponse(
        content=content,
        headers={"Cache-Control": "no-store, max-age=0"},
    )


RADIO_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Command Center Radio</title>
<style>
  :root { color-scheme: dark; }
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --cc-bg:        #05070a;
    --cc-bg-2:      #0a1015;
    --cc-panel:     #0f1820;
    --cc-line:      #1a2832;
    --cc-line-hi:   #2a3f4f;
    --cc-amber:     #ffb000;
    --cc-amber-2:   #ffd166;
    --cc-amber-dim: #6b4500;
    --cc-cyan:      #5ad3ff;
    --cc-green:     #34ff7a;
    --cc-red:       #ff4747;
    --cc-text:      #d4dde4;
    --cc-text-dim:  #5e6e7a;
  }

  html, body {
    width: 100%; height: 100%;
    overflow: hidden;
    background: var(--cc-bg);
    color: var(--cc-text);
    font-family: "JetBrains Mono", "Fira Code", "IBM Plex Mono",
                 ui-monospace, Menlo, Consolas, monospace;
    -webkit-font-smoothing: antialiased;
    user-select: none;
    -webkit-tap-highlight-color: transparent;
  }

  /* === Outer bezel / CRT frame ============================================ */
  .cc {
    position: fixed; inset: 0;
    display: grid;
    grid-template-rows: auto 1fr auto;
    gap: 10px;
    padding: 14px 18px;
    background:
      radial-gradient(ellipse at 50% -20%, rgba(255,176,0,0.06), transparent 50%),
      radial-gradient(ellipse at 50% 120%, rgba(90,211,255,0.05), transparent 55%),
      linear-gradient(180deg, #060a0e 0%, #04070a 100%);
  }
  .cc::before {
    content: "";
    position: absolute; inset: 0;
    pointer-events: none;
    background-image: repeating-linear-gradient(
      to bottom,
      rgba(255,255,255,0.025) 0px,
      rgba(255,255,255,0.025) 1px,
      transparent 1px,
      transparent 3px
    );
    mix-blend-mode: overlay;
    opacity: 0.55;
    z-index: 1;
  }
  .cc::after {
    content: "";
    position: absolute; inset: 0;
    pointer-events: none;
    box-shadow:
      inset 0 0 80px rgba(0,0,0,0.85),
      inset 0 0 8px rgba(255,176,0,0.06);
    z-index: 2;
  }

  /* === Header ============================================================= */
  .cc-head {
    position: relative; z-index: 3;
    display: flex; align-items: center; justify-content: space-between;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--cc-line);
    text-transform: uppercase;
    letter-spacing: 0.18em;
    font-size: 10px;
  }
  .cc-brand { display: flex; align-items: center; gap: 10px; }
  .cc-brand-bar {
    width: 4px; height: 14px;
    background: var(--cc-amber);
    box-shadow: 0 0 10px rgba(255,176,0,0.7);
  }
  .cc-brand-title { color: var(--cc-amber); font-weight: 700; }
  .cc-brand-id    { color: var(--cc-text-dim); }
  .cc-meta { display: flex; align-items: center; gap: 14px; color: var(--cc-text-dim); }
  .cc-meta b { color: var(--cc-text); font-weight: 600; }

  .cc-status { display: inline-flex; align-items: center; gap: 8px; }
  .cc-led {
    width: 9px; height: 9px; border-radius: 50%;
    background: var(--cc-amber-dim);
    box-shadow: 0 0 8px currentColor;
    color: var(--cc-amber-dim);
  }
  .cc-led.live    { background: var(--cc-green); color: var(--cc-green);
                    animation: cc-pulse 1.6s ease-in-out infinite; }
  .cc-led.error   { background: var(--cc-red);   color: var(--cc-red);
                    animation: cc-blink 0.45s steps(2,end) infinite; }
  @keyframes cc-pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.3; } }
  @keyframes cc-blink { 0% { opacity: 1; } 100% { opacity: 0.15; } }

  /* === Main display ======================================================= */
  .cc-main {
    position: relative; z-index: 3;
    display: grid;
    grid-template-columns: 1fr;
    gap: 10px;
    min-height: 0;
  }

  .cc-screen {
    position: relative;
    background:
      linear-gradient(180deg, rgba(255,176,0,0.05), transparent 60%),
      var(--cc-bg-2);
    border: 1px solid var(--cc-line);
    padding: 14px 16px 10px;
    display: grid;
    grid-template-rows: auto auto 1fr;
    gap: 10px;
    overflow: hidden;
  }
  .cc-screen::before {
    content: "";
    position: absolute; inset: 0;
    background:
      radial-gradient(ellipse at 30% 0%, rgba(255,176,0,0.08), transparent 60%);
    pointer-events: none;
  }

  .cc-row {
    display: flex; align-items: baseline; gap: 12px;
    position: relative;
  }
  .cc-label {
    color: var(--cc-text-dim);
    font-size: 10px; letter-spacing: 0.2em;
    text-transform: uppercase;
    min-width: 70px;
  }
  .cc-readout-channel {
    color: var(--cc-amber);
    font-size: clamp(20px, 4.2vw, 32px);
    font-weight: 700;
    letter-spacing: 0.08em;
    text-shadow: 0 0 8px rgba(255,176,0,0.45);
    line-height: 1.1;
  }
  .cc-readout-sub {
    color: var(--cc-text-dim);
    font-size: 11px; letter-spacing: 0.18em;
    text-transform: uppercase;
  }
  .cc-readout-src {
    color: var(--cc-cyan);
    font-size: 11px;
    letter-spacing: 0.05em;
    opacity: 0.7;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  }

  .cc-viz-wrap {
    position: relative;
    border: 1px solid var(--cc-line);
    background:
      linear-gradient(180deg, rgba(90,211,255,0.04), transparent 60%),
      #04080b;
    min-height: 90px;
  }
  .cc-viz {
    position: absolute; inset: 0;
    width: 100%; height: 100%;
    display: block;
  }
  .cc-viz-grid {
    position: absolute; inset: 0;
    pointer-events: none;
    background:
      linear-gradient(to right, rgba(90,211,255,0.07) 1px, transparent 1px) 0 0 / 10% 100%,
      linear-gradient(to bottom, rgba(90,211,255,0.07) 1px, transparent 1px) 0 0 / 100% 25%;
    opacity: 0.6;
  }

  /* === Control bar ======================================================== */
  .cc-controls {
    position: relative; z-index: 3;
    display: grid;
    grid-template-columns: 1fr auto auto auto;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    background: var(--cc-panel);
    border: 1px solid var(--cc-line);
  }

  /* Custom-styled native select for the station dropdown */
  .cc-select-wrap {
    position: relative;
    display: flex; align-items: center; gap: 10px;
    min-width: 0;
  }
  .cc-select-wrap .cc-label { min-width: 60px; }
  .cc-select {
    appearance: none; -webkit-appearance: none;
    flex: 1;
    background:
      linear-gradient(180deg, #0e1a23, #0a131a);
    color: var(--cc-amber);
    border: 1px solid var(--cc-line-hi);
    padding: 10px 36px 10px 12px;
    font-family: inherit;
    font-size: 13px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    cursor: pointer;
    outline: none;
    transition: border-color 120ms ease, box-shadow 120ms ease;
    min-width: 0;
    text-overflow: ellipsis;
  }
  .cc-select:hover  { border-color: var(--cc-amber-dim); }
  .cc-select:focus  { border-color: var(--cc-amber); box-shadow: 0 0 0 1px rgba(255,176,0,0.35), 0 0 12px rgba(255,176,0,0.15); }
  .cc-select option { background: #0a131a; color: var(--cc-text); }
  .cc-select-chev {
    position: absolute; right: 12px; top: 50%;
    transform: translateY(-50%);
    pointer-events: none;
    color: var(--cc-amber);
    font-size: 10px;
    opacity: 0.7;
  }

  .cc-btn {
    appearance: none;
    background: linear-gradient(180deg, #131e27, #0c141a);
    color: var(--cc-text);
    border: 1px solid var(--cc-line-hi);
    padding: 0;
    font-family: inherit;
    font-size: 12px;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    cursor: pointer;
    display: inline-flex; align-items: center; justify-content: center;
    gap: 6px;
    touch-action: manipulation;
    transition: border-color 120ms ease, transform 80ms ease, box-shadow 120ms ease;
  }
  .cc-btn:hover  { border-color: var(--cc-amber-dim); }
  .cc-btn:active { transform: translateY(1px); }

  /* Big circular play button */
  .cc-play {
    width: 56px; height: 56px;
    border-radius: 50%;
    border-color: var(--cc-amber);
    color: var(--cc-amber);
    background:
      radial-gradient(circle at 40% 30%, rgba(255,176,0,0.18), transparent 60%),
      radial-gradient(circle at 60% 80%, rgba(255,176,0,0.10), transparent 60%),
      linear-gradient(180deg, #1a2530, #0a131a);
    box-shadow:
      inset 0 0 12px rgba(255,176,0,0.18),
      0 0 18px rgba(255,176,0,0.20),
      0 0 0 1px rgba(255,176,0,0.30);
    font-size: 18px;
  }
  .cc-play:hover { box-shadow: inset 0 0 14px rgba(255,176,0,0.25), 0 0 22px rgba(255,176,0,0.30), 0 0 0 1px rgba(255,176,0,0.50); }

  .cc-stop {
    width: 44px; height: 44px;
    font-size: 13px;
    color: var(--cc-text-dim);
  }

  .cc-vol {
    display: flex; align-items: center; gap: 8px;
    padding: 0 10px;
    border: 1px solid var(--cc-line-hi);
    background: linear-gradient(180deg, #0e1a23, #0a131a);
    height: 44px;
    min-width: 170px;
  }
  .cc-vol .cc-label { min-width: auto; }
  .cc-vol input[type="range"] {
    -webkit-appearance: none; appearance: none;
    width: 100px; height: 3px;
    background: var(--cc-line-hi);
    outline: none;
  }
  .cc-vol input[type="range"]::-webkit-slider-thumb {
    -webkit-appearance: none; appearance: none;
    width: 14px; height: 14px;
    background: var(--cc-amber);
    border: 1px solid #000;
    box-shadow: 0 0 6px rgba(255,176,0,0.7);
    cursor: pointer;
  }
  .cc-vol input[type="range"]::-moz-range-thumb {
    width: 14px; height: 14px;
    background: var(--cc-amber);
    border: 1px solid #000;
    box-shadow: 0 0 6px rgba(255,176,0,0.7);
    cursor: pointer;
  }
  .cc-vol-readout {
    font-size: 11px; letter-spacing: 0.1em;
    color: var(--cc-text-dim);
    min-width: 24px; text-align: right;
  }

  .cc-viz-btn {
    height: 44px; padding: 0 12px;
    color: var(--cc-text-dim);
    display: inline-flex; align-items: center; gap: 8px;
  }
  .cc-viz-btn.active { color: var(--cc-cyan); border-color: var(--cc-cyan); box-shadow: 0 0 10px rgba(90,211,255,0.25); }

  @media (max-width: 640px) {
    .cc-controls { grid-template-columns: 1fr auto; grid-auto-rows: auto; }
    .cc-vol { grid-column: 1 / -1; min-width: 0; width: 100%; }
    .cc-viz-btn { grid-column: 1 / -1; justify-content: center; }
  }
</style>
</head>
<body>

<div class="cc">
  <header class="cc-head">
    <div class="cc-brand">
      <span class="cc-brand-bar"></span>
      <span class="cc-brand-title">COMMAND CENTER // AUDIO</span>
      <span class="cc-brand-id">CCR-01</span>
    </div>
    <div class="cc-meta">
      <span>SIG <b id="cc-bitrate">--</b></span>
      <span>TIME <b id="cc-clock">--:--:--</b></span>
      <span class="cc-status">
        <span id="cc-led" class="cc-led"></span>
        <span id="cc-status-text">STANDBY</span>
      </span>
    </div>
  </header>

  <main class="cc-main">
    <section class="cc-screen">
      <div class="cc-row">
        <span class="cc-label">CHANNEL</span>
        <span id="cc-channel" class="cc-readout-channel">--- NO SIGNAL ---</span>
      </div>
      <div class="cc-row">
        <span class="cc-label">CARRIER</span>
        <span id="cc-src" class="cc-readout-src">awaiting selection</span>
      </div>
      <div class="cc-viz-wrap">
        <div class="cc-viz-grid"></div>
        <canvas id="cc-viz" class="cc-viz"></canvas>
      </div>
    </section>
  </main>

  <footer class="cc-controls">
    <div class="cc-select-wrap">
      <span class="cc-label">STATION</span>
      <select id="cc-station" class="cc-select" aria-label="Station">
        <option value="">-- SELECT TRANSMISSION --</option>
      </select>
      <span class="cc-select-chev">&#9662;</span>
    </div>

    <button type="button" id="cc-play" class="cc-btn cc-play" aria-label="Play / pause">
      <span id="cc-play-icon">&#9658;</span>
    </button>
    <button type="button" id="cc-stop" class="cc-btn cc-stop" aria-label="Stop">&#9632;</button>

    <div class="cc-vol">
      <span class="cc-label">VOL</span>
      <input type="range" id="cc-volume" min="0" max="1" step="0.01" value="0.8">
      <span id="cc-vol-read" class="cc-vol-readout">80</span>
    </div>

    <button type="button" id="cc-viz-toggle" class="cc-btn cc-viz-btn">
      <span>VIZ</span><span id="cc-viz-state">OFF</span>
    </button>
  </footer>
</div>

<audio id="cc-audio" preload="none"></audio>

<script>
(function(){
  const STATIONS = [
    { id: "groovesalad",  name: "GROOVE SALAD",       sub: "DOWNTEMPO / AMBIENT",      url: "https://ice2.somafm.com/groovesalad-128-mp3",  br: "128K" },
    { id: "dronezone",    name: "DRONE ZONE",         sub: "ATMOSPHERIC / SPACE",      url: "https://ice2.somafm.com/dronezone-128-mp3",    br: "128K" },
    { id: "reggae",       name: "HEAVYWEIGHT REGGAE", sub: "ROOTS / DUB",              url: "https://ice2.somafm.com/reggae-128-mp3",       br: "128K" },
    { id: "deepspaceone", name: "DEEP SPACE ONE",     sub: "DEEP AMBIENT / ELECTRONIC", url: "https://ice2.somafm.com/deepspaceone-128-mp3", br: "128K" },
    { id: "secretagent",  name: "SECRET AGENT",       sub: "SPY JAZZ / LOUNGE",        url: "https://ice2.somafm.com/secretagent-128-mp3",  br: "128K" },
    { id: "defcon",       name: "DEF CON RADIO",      sub: "HACKER ELECTRONICA",       url: "https://ice2.somafm.com/defcon-128-mp3",       br: "128K" },
    { id: "missioncontrol", name: "MISSION CONTROL",  sub: "AMBIENT + NASA COMMS",     url: "https://ice2.somafm.com/missioncontrol-128-mp3", br: "128K" },
    { id: "spacestation", name: "SPACE STATION",      sub: "AMBIENT ELECTRONICA",      url: "https://ice2.somafm.com/spacestation-128-mp3", br: "128K" },
  ];

  const audio      = document.getElementById("cc-audio");
  const select     = document.getElementById("cc-station");
  const channel    = document.getElementById("cc-channel");
  const srcReadout = document.getElementById("cc-src");
  const led        = document.getElementById("cc-led");
  const statusText = document.getElementById("cc-status-text");
  const playBtn    = document.getElementById("cc-play");
  const playIcon   = document.getElementById("cc-play-icon");
  const stopBtn    = document.getElementById("cc-stop");
  const volInput   = document.getElementById("cc-volume");
  const volRead    = document.getElementById("cc-vol-read");
  const vizBtn     = document.getElementById("cc-viz-toggle");
  const vizState   = document.getElementById("cc-viz-state");
  const vizCanvas  = document.getElementById("cc-viz");
  const ctx        = vizCanvas.getContext("2d");
  const bitrate    = document.getElementById("cc-bitrate");
  const clock      = document.getElementById("cc-clock");

  // Populate dropdown
  STATIONS.forEach((s, i) => {
    const o = document.createElement("option");
    o.value = String(i);
    o.textContent = `${String(i+1).padStart(2,"0")}  ${s.name}  -  ${s.sub}`;
    select.appendChild(o);
  });

  const state = { current: null, vizEnabled: false };

  function setStatus(text, mode) {
    statusText.textContent = text;
    led.className = "cc-led" + (mode ? " " + mode : "");
  }
  function setPlayIcon(playing) {
    playIcon.innerHTML = playing ? "&#10074;&#10074;" : "&#9658;";
  }

  function selectStation(idx) {
    const s = STATIONS[idx];
    if (!s) return;
    state.current = s;
    channel.textContent = s.name;
    srcReadout.textContent = s.url;
    bitrate.textContent = s.br || "--";
    audio.src = s.url;
    audio.load();
    setStatus("ACQUIRING SIGNAL...", "");
    audio.play().catch(err => setStatus("FAULT: " + (err.message || "play blocked"), "error"));
  }

  select.addEventListener("change", () => {
    const idx = parseInt(select.value, 10);
    if (!isNaN(idx)) selectStation(idx);
  });

  playBtn.addEventListener("click", () => {
    if (!state.current) {
      if (STATIONS.length) { select.value = "0"; selectStation(0); }
      return;
    }
    if (audio.paused) audio.play().catch(err => setStatus("FAULT: " + err.message, "error"));
    else audio.pause();
  });

  stopBtn.addEventListener("click", () => {
    audio.pause();
    audio.removeAttribute("src");
    audio.load();
    state.current = null;
    channel.textContent = "--- NO SIGNAL ---";
    srcReadout.textContent = "awaiting selection";
    bitrate.textContent = "--";
    select.value = "";
    setStatus("STANDBY", "");
    setPlayIcon(false);
  });

  function applyVol(v) { audio.volume = v; volRead.textContent = String(Math.round(v*100)); }
  volInput.addEventListener("input", e => applyVol(parseFloat(e.target.value)));
  applyVol(parseFloat(volInput.value));

  audio.addEventListener("playing", () => { setPlayIcon(true);  setStatus("TRANSMITTING", "live"); });
  audio.addEventListener("pause",   () => { setPlayIcon(false); if (state.current) setStatus("PAUSED", ""); });
  audio.addEventListener("waiting", () => setStatus("BUFFERING...", ""));
  audio.addEventListener("stalled", () => setStatus("STALLED", "error"));
  audio.addEventListener("error",   () => { setStatus("SIGNAL LOST", "error"); setPlayIcon(false); });

  // Clock
  function tick() {
    const d = new Date();
    const hh = String(d.getHours()).padStart(2,"0");
    const mm = String(d.getMinutes()).padStart(2,"0");
    const ss = String(d.getSeconds()).padStart(2,"0");
    clock.textContent = `${hh}:${mm}:${ss}`;
  }
  tick(); setInterval(tick, 1000);

  // Visualizer
  let audioCtx = null, analyser = null, dataArray = null, rafId = null;

  function resizeCanvas() {
    const r = vizCanvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    vizCanvas.width  = Math.max(1, Math.floor(r.width  * dpr));
    vizCanvas.height = Math.max(1, Math.floor(r.height * dpr));
    ctx.setTransform(dpr,0,0,dpr,0,0);
  }
  resizeCanvas();
  if (typeof ResizeObserver !== "undefined") new ResizeObserver(resizeCanvas).observe(vizCanvas);
  window.addEventListener("resize", resizeCanvas);

  function drawIdle() {
    const w = vizCanvas.clientWidth, h = vizCanvas.clientHeight;
    ctx.clearRect(0,0,w,h);
    ctx.strokeStyle = "rgba(255,176,0,0.25)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, h/2);
    for (let x = 0; x < w; x += 6) {
      ctx.lineTo(x, h/2 + Math.sin((x + Date.now()*0.002) * 0.05) * 1.5);
    }
    ctx.stroke();
  }
  let idleRaf = null;
  function idleLoop() { drawIdle(); idleRaf = requestAnimationFrame(idleLoop); }
  idleLoop();

  function drawBars() {
    rafId = requestAnimationFrame(drawBars);
    if (!analyser || !dataArray) return;
    analyser.getByteFrequencyData(dataArray);
    const w = vizCanvas.clientWidth, h = vizCanvas.clientHeight;
    ctx.clearRect(0,0,w,h);
    const bars = dataArray.length;
    const barW = w / bars;
    for (let i = 0; i < bars; i++) {
      const v = dataArray[i] / 255;
      const barH = Math.max(1, v * h * 0.95);
      const hue = 40 - v * 40;            // amber -> red shift on peaks
      const grad = ctx.createLinearGradient(0, h, 0, h - barH);
      grad.addColorStop(0, `hsla(${hue}, 100%, 50%, 0.95)`);
      grad.addColorStop(1, `hsla(${hue + 30}, 100%, 65%, 0.20)`);
      ctx.fillStyle = grad;
      ctx.fillRect(i * barW + 0.5, h - barH, Math.max(1, barW - 1), barH);
    }
  }

  function enableViz() {
    if (audioCtx) return true;
    try {
      audio.crossOrigin = "anonymous";
      if (state.current) {
        const playing = !audio.paused;
        audio.src = state.current.url; audio.load();
        if (playing) audio.play().catch(()=>{});
      }
      const AC = window.AudioContext || window.webkitAudioContext;
      audioCtx = new AC();
      const src = audioCtx.createMediaElementSource(audio);
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      src.connect(analyser); analyser.connect(audioCtx.destination);
      dataArray = new Uint8Array(analyser.frequencyBinCount);
      if (idleRaf) { cancelAnimationFrame(idleRaf); idleRaf = null; }
      drawBars();
      return true;
    } catch (e) {
      audioCtx = null; analyser = null; dataArray = null;
      return false;
    }
  }
  function disableViz() {
    if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
    if (audioCtx) { try { audioCtx.close(); } catch(_){} }
    audioCtx = null; analyser = null; dataArray = null;
    audio.removeAttribute("crossorigin");
    if (state.current) {
      const playing = !audio.paused;
      audio.src = state.current.url; audio.load();
      if (playing) audio.play().catch(()=>{});
    }
    if (!idleRaf) idleLoop();
  }
  vizBtn.addEventListener("click", () => {
    if (state.vizEnabled) {
      state.vizEnabled = false;
      vizState.textContent = "OFF";
      vizBtn.classList.remove("active");
      disableViz();
    } else {
      const ok = enableViz();
      state.vizEnabled = ok;
      vizState.textContent = ok ? "ON" : "BLOCKED";
      if (ok) vizBtn.classList.add("active");
    }
  });
})();
</script>
</body>
</html>"""


RADIO_HTML_REMOTE = os.getenv(
    "RADIO_HTML_URL",
    "https://raw.githubusercontent.com/Jdoink/sovereignty_stack/main/command-center-radio/radio.html",
)


@app.get("/radio", response_class=HTMLResponse)
async def radio() -> HTMLResponse:
    # Try to fetch the latest radio.html from GitHub so updates flow without
    # rebuilding this container. If GitHub is unreachable for any reason, fall
    # back to the version embedded in this Python file.
    if http_client is not None:
        try:
            r = await http_client.get(RADIO_HTML_REMOTE, timeout=httpx.Timeout(5.0))
            if r.status_code == 200 and r.text:
                return HTMLResponse(
                    content=r.text,
                    headers={"Cache-Control": "no-store, max-age=0"},
                )
        except Exception:
            logger.exception("Failed to fetch %s, falling back to embedded copy", RADIO_HTML_REMOTE)

    return HTMLResponse(
        content=RADIO_HTML,
        headers={"Cache-Control": "no-store, max-age=0"},
    )
