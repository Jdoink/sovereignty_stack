# Ticker Service

## What this service does

This service collects crypto and protocol data from multiple APIs, formats it into simple ticker lines, and exposes JSON/text/HTML ticker endpoints for Grafana.

Endpoints:
- `GET /health` → `{"status":"ok"}`
- `GET /ticker` → JSON list with `text` fields
- `GET /ticker-line` → plain text single-line ticker
- `GET /ticker-html` → standalone scrolling HTML ticker page (for iframe embed)
- `GET /radio` → standalone Command Center Radio page (for iframe embed in Grafana)

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


## Grafana Business Text panel setup (recommended)

This is the canonical setup. It uses the **Business Text** panel (`marcusolsson-dynamictext-panel`) + the **Infinity** data source + the `/ticker` JSON endpoint + the `/ticker.css` stylesheet endpoint served by this service. The marquee renders directly in the Grafana panel DOM — no iframe, no sanitization issues, scales across the full panel width on any device.

**Step 1 — Add the panel.** Add a new panel, set Visualization to **Business Text**.

**Step 2 — Query.** Set the data source to **Infinity**:
- Type: `JSON`
- Source: `URL`
- Format: `Table`
- URL: `http://192.168.1.189:8787/ticker`
- Columns: one column with Selector `text`, Title `text`, Type `string`

**Step 3 — Load the marquee styles.** In the panel options, find **CSS Styles → New Resource → URL** and paste:

```
http://192.168.1.189:8787/ticker.css
```

Click **Add**. The Business Text plugin will load the marquee CSS from the service on each render.

**Step 4 — Content template.** In the panel options' **Content** editor (set Content Language to **HTML**), paste:

```html
<div class="ssticker-wrap">
  <div class="ssticker-track">
    <span class="ssticker-copy">{{#each data}}{{text}} | {{/each}}</span><span class="ssticker-copy">{{#each data}}{{text}} | {{/each}}</span>
  </div>
</div>
```

**Step 5 — Render mode.** Set **Rendering** to **All rows** (not "Every row"). This makes the template render once with all data, so the marquee gets the full ticker line.

**Step 6 — Refresh.** Set the dashboard refresh interval to **30s** (top-right of the dashboard). The data refreshes via Grafana's panel-refresh; the scroll animation never restarts because the CSS is loaded once and only the text content changes.

The marquee scales to the panel via `font-size: clamp(20px, 10vh, 80px)` — resize the panel taller or wider and the text scales with it. The scroll loop is seamless: the line is rendered twice in a single track and animates `translate3d(0) → translate3d(-50%)`, so when copy A scrolls off the left, copy B is already where copy A started.

### Optional — standalone iframe page

For embedding outside Grafana (kiosk browser pointed straight at the URL, a TV display, etc.), the service also exposes a complete standalone marquee page at `http://192.168.1.189:8787/ticker-html`. Open it directly in a browser — same styling, with a built-in 30-second JS poll for fresh data. **Note:** this works as a standalone page but does **not** work reliably embedded in a Grafana Text panel iframe, because Grafana sanitizes inline iframe styles and the iframe collapses to its default intrinsic size. Use the Business Text setup above for Grafana.

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
