# Ticker Service

## What this service does

This service collects crypto and protocol data from multiple APIs, formats it into simple ticker lines, and exposes JSON/text/HTML ticker endpoints for Grafana.

Endpoints:
- `GET /health` → `{"status":"ok"}`
- `GET /ticker` → JSON list with `text` fields
- `GET /ticker-line` → plain text single-line ticker
- `GET /ticker-html` → standalone scrolling HTML ticker page (for iframe embed)

Data sources:
- CoinGecko prices (BTC, ETH, LINK, AAVE, CRV)
- Etherscan ETH gas oracle
- DeFiLlama protocol TVL (Aave, Curve)

It uses in-memory caching to reduce API calls and improve dashboard reliability.

Chainlink remains included as **LINK price only** for now (not as a TVL metric).

## Environment configuration

1. Copy the example file:

```bash
cp .env.example .env
```

2. Edit `.env`:

```env
ETHERSCAN_API_KEY=your_real_key_here
```

Notes:
- Never commit `.env`.
- Keep this service private on LAN/Tailscale.

## Run with Docker Compose

```bash
docker compose up -d --build
```

Check logs:

```bash
docker compose logs -f
```

Stop:

```bash
docker compose down
```

## Test endpoints

Health check:

```bash
curl http://localhost:8787/health
```

Ticker output:

```bash
curl http://localhost:8787/ticker
```


## Grafana Text panel iframe setup (recommended)

Use a Grafana **Text panel** in **HTML mode**, turn on the panel's "Transparent background" toggle, and paste:

```html
<div style="position:relative;width:100%;height:100%;min-height:120px;">
  <iframe
    src="http://192.168.1.189:8787/ticker-html"
    style="position:absolute;inset:0;width:100%;height:100%;border:0;margin:0;padding:0;display:block;background:transparent;"
    frameborder="0"
    scrolling="no"
    allowtransparency="true">
  </iframe>
</div>
```

The wrapping `<div>` with `position:relative` plus the absolutely-positioned iframe is what makes the iframe stretch to fill the panel — without that wrapper, `height:100%` on a bare iframe collapses to the iframe's default intrinsic height and you'll see a small fixed-size box inside a much larger panel.

The page itself uses `clamp(22px, 10vh, 96px)` font sizing, so the text scales with the panel's height as you resize it. Data refreshes every 30s in place (no page reload, no scroll snap-back). Scroll loop is seamless — the line is rendered twice and the animation translates by exactly 50%, so the next pass picks up where the previous one left off.

## Grafana Infinity setup

In Grafana Infinity datasource:
- Type: JSON
- Source: URL
- Format: Table
- URL: `http://<your-pi-ip>:8787/ticker`

Columns:
- Selector: `text`
- Title: `text`
- Type: `string`

## Business Ticker usage

In Business Ticker panel:
- Use the Infinity query that reads `/ticker`
- Set display field to `text`
- The panel will scroll each item from the returned JSON list

## Troubleshooting

- **No gas line appears**: check `ETHERSCAN_API_KEY` in `.env` and restart the container.
- **Only warning lines appear**: upstream API may be temporarily failing; check logs with `docker compose logs -f`.
- **Port conflict on 8787**: stop the other service using 8787 before starting ticker-service.
- **Grafana can’t reach service**: verify IP/port and test `curl http://<pi-ip>:8787/health` from Grafana host.
- **Stale values**: expected within cache TTLs (60s prices/gas, 10m TVL).
- **One TVL protocol missing**: service now fails TVL per protocol (Aave/Curve independently), so one failure does not hide the other.

- **DeFiLlama response format changed**: this service now handles multiple TVL shapes, but if warnings persist, check logs for protocol-specific parse errors.
