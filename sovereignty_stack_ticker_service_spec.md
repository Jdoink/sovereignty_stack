# Sovereignty Stack — Crypto Ticker Service Spec

## Purpose

Build a small local service that turns messy crypto/protocol APIs into one clean JSON feed for Grafana’s Business Ticker panel.

Instead of fighting Grafana transformations manually, this service should collect the data, format it cleanly, cache it safely, and expose one simple endpoint:

```text
GET http://<raspi-ip>:8787/ticker
```

Grafana should only need to read the `text` field from the returned JSON.

## Target Architecture

```text
CoinGecko + Etherscan + DeFiLlama
        ↓
Local Python FastAPI ticker service
        ↓
GET /ticker
        ↓
Grafana Business Ticker
        ↓
Sovereignty Stack Command Center
```

## Repo Structure

Create a GitHub repo or folder named:

```text
sovereignty-stack
```

Suggested structure:

```text
sovereignty-stack/
  ticker-service/
    server.py
    requirements.txt
    docker-compose.yml
    .env.example
    .gitignore
    README.md
```

## Service Requirements

Use:

```text
Python
FastAPI
httpx
python-dotenv
uvicorn
```

The service should expose:

```text
GET /health
```

Returns:

```json
{"status":"ok"}
```

And:

```text
GET /ticker
```

Returns a JSON list like:

```json
[
  {"text": "BTC $76,982"},
  {"text": "ETH $2,129"},
  {"text": "LINK $9.61"},
  {"text": "AAVE $265"},
  {"text": "CRV $0.62"},
  {"text": "ETH GAS Safe 1 / Std 2 / Fast 3 gwei"},
  {"text": "Aave TVL $22.4B"},
  {"text": "Curve TVL $2.1B"},
  {"text": "Chainlink TVL $18.8B"}
]
```

## Data Sources

### 1. CoinGecko Prices

Use CoinGecko simple price API for:

```text
bitcoin
ethereum
chainlink
aave
curve-dao-token
```

Endpoint:

```text
https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,chainlink,aave,curve-dao-token&vs_currencies=usd&include_24hr_change=true&include_last_updated_at=true
```

Fields to use:

```text
bitcoin.usd
ethereum.usd
chainlink.usd
aave.usd
curve-dao-token.usd
```

Optional later:

```text
bitcoin.usd_24h_change
ethereum.usd_24h_change
chainlink.usd_24h_change
aave.usd_24h_change
curve-dao-token.usd_24h_change
last_updated_at
```

Important: CoinGecko public data is cached. Do not hit it every 10 seconds. Cache locally for at least 60 seconds.

### 2. Etherscan Gas Oracle

Use Etherscan v2 gas oracle.

API key should come from environment variable:

```text
ETHERSCAN_API_KEY
```

Endpoint pattern:

```text
https://api.etherscan.io/v2/api?chainid=1&module=gastracker&action=gasoracle&apikey=${ETHERSCAN_API_KEY}
```

Fields to use:

```text
result.SafeGasPrice
result.ProposeGasPrice
result.FastGasPrice
result.suggestBaseFee
```

Ticker format:

```text
ETH GAS Safe {safe} / Std {standard} / Fast {fast} gwei
```

Cache this for 30–60 seconds.

### 3. DeFiLlama Protocol TVL

Use DeFiLlama protocol endpoints:

```text
https://api.llama.fi/protocol/aave
https://api.llama.fi/protocol/curve-dex
https://api.llama.fi/protocol/chainlink
```

Primary field:

```text
tvl
```

Ticker format:

```text
Aave TVL $22.4B
Curve TVL $2.1B
Chainlink TVL $18.8B
```

Format large numbers cleanly:

```text
$1,250 → $1.25K
$1,250,000 → $1.25M
$1,250,000,000 → $1.25B
```

Cache this for 5–15 minutes.

## Formatting Rules

Prices:

```text
BTC and ETH: no decimals or max 2 decimals
LINK, AAVE, CRV: 2 decimals
```

Examples:

```text
BTC $76,982
ETH $2,129
LINK $9.61
AAVE $265.44
CRV $0.62
```

Gas:

```text
ETH GAS Safe 1 / Std 2 / Fast 3 gwei
```

TVL:

```text
Aave TVL $22.4B
Curve TVL $2.1B
Chainlink TVL $18.8B
```

## Error Handling

If one API fails, do not crash the service.

Instead:

- Return all successful ticker items.
- Add one warning item if useful.

Example:

```json
[
  {"text": "BTC $76,982"},
  {"text": "ETH $2,129"},
  {"text": "Gas data unavailable"}
]
```

The service should log errors clearly, but Grafana should still receive valid JSON.

## Caching

Use simple in-memory caching.

Suggested TTLs:

```text
CoinGecko prices: 60 seconds
Etherscan gas: 30–60 seconds
DeFiLlama TVL: 300–900 seconds
```

Reason:

- Avoid rate limits.
- Reduce load.
- Keep dashboard reliable.
- Public price APIs are not true tick-by-tick feeds anyway.

## Environment Variables

Create `.env.example`:

```text
ETHERSCAN_API_KEY=
PORT=8787
```

The real `.env` file should never be committed.

Add `.gitignore`:

```text
.env
__pycache__/
*.pyc
```

## Docker Compose

Expose port:

```text
8787:8787
```

Example service name:

```text
ticker-service
```

The container should restart unless stopped.

## Grafana Integration

Once running, Grafana Infinity should point to:

```text
http://192.168.1.189:8787/ticker
```

Or through Tailscale:

```text
http://100.82.61.96:8787/ticker
```

Infinity settings:

```text
Type: JSON
Source: URL
Format: Table
URL: http://192.168.1.189:8787/ticker
```

Column:

```text
Selector: text
Title: text
Type: string
```

Business Ticker should display the `text` field.

## Future Upgrades

After the basic ticker works, add:

```text
24h price change arrows
green/red formatting
Fear & Greed Index
stablecoin supply
Aave borrow/supply rates
Curve volume/fees
Chainlink fees/revenue/TVS
whale alerts
wallet tracking
onchain alerts
news headlines
AI-generated market summaries
```

## Security Notes

Never paste API keys into code.

Use:

```text
.env
```

or CasaOS/Docker environment variables.

If an API key is shown in a screenshot or pasted into chat, rotate it.

Do not expose this service publicly yet. Keep access private through local network or Tailscale.

## Codex Build Prompt

Use this prompt with Codex:

```text
Build a small Python FastAPI service for my Raspberry Pi homelab called sovereignty-stack ticker-service.

Goal:
Expose a local JSON endpoint at GET /ticker that returns clean ticker items for Grafana Business Ticker.

Data sources:
1. CoinGecko simple price API for bitcoin, ethereum, chainlink, aave, curve-dao-token.
2. Etherscan gas oracle API for Ethereum mainnet gas. API key should come from ETHERSCAN_API_KEY env var.
3. DeFiLlama protocol API for aave, curve-dex, and chainlink TVL.

Requirements:
- Use FastAPI.
- Use httpx.
- Use python-dotenv.
- Add simple in-memory caching.
- CoinGecko cache TTL: 60 seconds.
- Etherscan gas cache TTL: 60 seconds.
- DeFiLlama TVL cache TTL: 10 minutes.
- Add graceful error handling. If one API fails, still return the rest of the ticker.
- Endpoint GET /ticker should return JSON like:
[
  {"text":"BTC $76,982"},
  {"text":"ETH $2,129"},
  {"text":"LINK $9.61"},
  {"text":"AAVE $265"},
  {"text":"CRV $0.62"},
  {"text":"ETH GAS Safe 1 / Std 2 / Fast 3 gwei"},
  {"text":"Aave TVL $22.4B"},
  {"text":"Curve TVL $2.1B"},
  {"text":"Chainlink TVL $18.8B"}
]
- Add GET /health returning {"status":"ok"}.
- Include docker-compose.yml exposing port 8787.
- Include .env.example with ETHERSCAN_API_KEY= and PORT=8787.
- Include .gitignore excluding .env and Python cache files.
- Include README with setup instructions and Grafana Infinity instructions.
- Keep code beginner-readable with comments.
```
