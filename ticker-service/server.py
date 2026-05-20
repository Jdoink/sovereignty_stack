import asyncio
import html
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, PlainTextResponse

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


@app.get("/ticker-html", response_class=HTMLResponse)
async def ticker_html() -> HTMLResponse:
    items = await build_ticker_items()
    line = html.escape(items_to_line(items))

    content = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta http-equiv="refresh" content="60" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>Sovereignty Ticker</title>
  <style>
    :root {{
      color-scheme: dark;
      --ticker-green: #39ff7a;
      --bg: rgba(0, 0, 0, 0.88);
      --scanline: rgba(57, 255, 122, 0.06);
    }}

    * {{ box-sizing: border-box; }}

    html, body {{
      width: 100%;
      height: 100%;
      margin: 0;
      padding: 0;
      border: 0;
      overflow: hidden;
      background: transparent;
      scrollbar-width: none;
      -ms-overflow-style: none;
      font-family: "SFMono-Regular", Menlo, Consolas, "Liberation Mono", monospace;
    }}

    body::-webkit-scrollbar {{
      width: 0;
      height: 0;
      display: none;
    }}

    .ticker-root {{
      position: fixed;
      inset: 0;
      width: 100vw;
      height: 100vh;
      margin: 0;
      padding: 0;
      overflow: hidden;
      background:
        linear-gradient(180deg, rgba(0, 0, 0, 0.78), var(--bg)),
        repeating-linear-gradient(
          0deg,
          transparent 0 3px,
          var(--scanline) 3px 4px
        );
      display: flex;
      align-items: center;
      justify-content: flex-start;
    }}

    .ticker-track {{
      display: inline-block;
      white-space: nowrap;
      will-change: transform;
      margin: 0;
      padding-left: 100vw;
      color: var(--ticker-green);
      font-size: clamp(18px, 2.6vw, 52px);
      line-height: 1;
      letter-spacing: 0.02em;
      font-weight: 600;
      text-shadow:
        0 0 4px rgba(57, 255, 122, 0.55),
        0 0 12px rgba(57, 255, 122, 0.35),
        0 0 20px rgba(57, 255, 122, 0.2);
      animation: ticker-scroll 44s linear infinite;
    }}

    @media (max-width: 900px) {{
      .ticker-track {{
        font-size: clamp(16px, 4.8vw, 30px);
        animation-duration: 36s;
      }}
    }}

    @media (min-width: 1800px) {{
      .ticker-track {{
        font-size: clamp(34px, 2.4vw, 64px);
        animation-duration: 52s;
      }}
    }}

    @keyframes ticker-scroll {{
      0% {{ transform: translate3d(0, 0, 0); }}
      100% {{ transform: translate3d(-100%, 0, 0); }}
    }}
  </style>
</head>
<body>
  <main class="ticker-root" aria-label="Live ticker">
    <div class="ticker-track">{line}</div>
  </main>
</body>
</html>"""

    return HTMLResponse(content=content)
