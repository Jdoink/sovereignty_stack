import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("ticker-service")

app = FastAPI(title="Sovereignty Stack Ticker Service")

PORT = int(os.getenv("PORT", "8787"))
ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "").strip()

COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/simple/price"
    "?ids=bitcoin,ethereum,chainlink,aave,curve-dao-token"
    "&vs_currencies=usd&include_24hr_change=true&include_last_updated_at=true"
)
ETHERSCAN_URL = (
    "https://api.etherscan.io/v2/api"
    "?chainid=1&module=gastracker&action=gasoracle"
)
DEFILLAMA_PROTOCOLS = {
    "Aave": "https://api.llama.fi/protocol/aave",
    "Curve": "https://api.llama.fi/protocol/curve-dex",
    "Chainlink": "https://api.llama.fi/protocol/chainlink",
}

# in-memory cache: key -> (expires_at_unix, data)
cache: Dict[str, Tuple[float, Any]] = {}


async def fetch_json(url: str, params: Optional[Dict[str, str]] = None) -> Any:
    timeout = httpx.Timeout(10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, params=params)
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
    if symbol in {"BTC", "ETH"}:
        rounded = round(value)
        return f"${rounded:,.0f}"
    return f"${value:,.2f}"


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

    data = await fetch_json(ETHERSCAN_URL, params={"apikey": ETHERSCAN_API_KEY})
    result = data.get("result", {})
    gas = {
        "safe": str(result.get("SafeGasPrice", "?")),
        "standard": str(result.get("ProposeGasPrice", "?")),
        "fast": str(result.get("FastGasPrice", "?")),
    }
    set_cached(cache_key, gas, ttl_seconds=60)
    return gas


async def get_tvl_data() -> Dict[str, float]:
    cache_key = "defillama_tvl"
    cached = get_cached(cache_key)
    if cached is not None:
        return cached

    tvl: Dict[str, float] = {}
    for name, url in DEFILLAMA_PROTOCOLS.items():
        payload = await fetch_json(url)
        tvl[name] = float(payload.get("tvl", 0.0))

    set_cached(cache_key, tvl, ttl_seconds=600)
    return tvl


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/ticker")
async def ticker() -> List[Dict[str, str]]:
    items: List[Dict[str, str]] = []

    # Run sources concurrently. Each section has independent error handling.
    results = await asyncio.gather(
        get_coingecko_prices(),
        get_eth_gas(),
        get_tvl_data(),
        return_exceptions=True,
    )

    prices_result, gas_result, tvl_result = results

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

    if isinstance(tvl_result, Exception):
        logger.exception("DeFiLlama TVL section failed", exc_info=tvl_result)
        items.append({"text": "Warning: TVL data unavailable"})
    else:
        for name in ["Aave", "Curve", "Chainlink"]:
            items.append({"text": f"{name} TVL {format_compact_usd(tvl_result[name])}"})

    return items


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("server:app", host="0.0.0.0", port=PORT, reload=False)
