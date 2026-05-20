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
  <meta charset=\"utf-8\" />
  <meta http-equiv=\"refresh\" content=\"60\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Sovereignty Ticker</title>
  <style>
    :root {{ color-scheme: dark; }}
    html, body {{
      margin: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: rgba(0,0,0,0.9);
      font-family: "SFMono-Regular", Menlo, Consolas, "Liberation Mono", monospace;
    }}
    .wrap {{
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      overflow: hidden;
    }}
    .track {{
      white-space: nowrap;
      color: #3CFF7A;
      font-size: clamp(28px, 4vw, 46px);
      line-height: 1.1;
      text-shadow: 0 0 8px rgba(60,255,122,0.6);
      padding-left: 100%;
      animation: scroll-left 38s linear infinite;
    }}
    @keyframes scroll-left {{
      0% {{ transform: translateX(0); }}
      100% {{ transform: translateX(-100%); }}
    }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"track\">{line}</div>
  </div>
</body>
</html>"""

    return HTMLResponse(content=content)
