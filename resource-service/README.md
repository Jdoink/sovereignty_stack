# resource-service

Serves the **Sovereign Resource Portal** — the Command Center's curated launchpad
for free media, public-domain archives, learning, privacy, self-hosting, AI, and
Web3 resources. This is the discovery layer of the broader Command Center Media
Layer (Portal → Media Theater → Music Player → Local Archive).

It follows the same pattern as `ticker-service` and `wallet-service`: a small
FastAPI app that serves a standalone HTML page (same-origin, so video / fullscreen
/ JS work cleanly when embedded in Grafana as an iframe). The page itself is
fetched live from this repo's `main` branch, so you can update the UI by pushing
to GitHub — no container rebuild required.

## Endpoints

| Method | Path      | Description |
|--------|-----------|-------------|
| `GET`  | `/`        | Redirects to `/portal` |
| `GET`  | `/portal`  | The Sovereign Resource Portal page (latest `command-center-portal/portal.html` from GitHub `main`, with an offline fallback notice) |
| `GET`  | `/theater` | The Media Theater page (latest `command-center-portal/theater.html` from GitHub `main`) |
| `GET`  | `/health`  | Liveness check |

## V1 features

- **Curated launcher** — touch-friendly category cards (FMHY index, Music/Audio,
  Books, Learning, Privacy, Self-Hosting, AI, Web3) opening in new tabs with
  `rel="noopener noreferrer"`.
- **Federated search** — type a term once and jump to it on a trusted source
  (Internet Archive, Project Gutenberg, Open Library, Wikipedia, Library of
  Congress, GitHub). Implemented with live-updating `target="_blank"` anchors so
  it works inside the Grafana iframe without popup blocking.
- **Safety banner** — FMHY is framed as a reference directory only; legal /
  public-domain / open-source resources are prioritized.

## Media Theater (`/theater`)

Internet Archive search + in-page playback. Type a query (or pick a preset),
toggle Video / Audio, and tap a result to play it — resolved entirely
client-side via archive.org's public API (`advancedsearch.php` →
`metadata/<id>` → `download/<id>/<file>`, the same flow the radio uses), so no
API key or backend proxy is needed. Picks the best web-playable container
(MP4/WebM/OGV for video, MP3/OGG for audio), has a fullscreen button, links each
item back to archive.org, and includes an "advanced" direct-URL player as a
fallback. Legal-by-construction: only public-domain / Creative-Commons archive
content and user-supplied direct URLs.

> The Grafana iframe embedding `/theater` should include `allow="fullscreen"`
> so the fullscreen button works inside the panel.

## Roadmap (not yet built)

- **Resource Vault**: `RESOURCE_DATA_PATH` JSON (read + write "Add to Vault"),
  link-health checks, and truthful downloaded/backed-up status by inspecting the
  external drive. Save-to-vault hooks from both the Portal and the Theater.

## Run locally

```bash
cd resource-service
cp .env.example .env   # optional; defaults work out of the box
docker compose up -d --build
# portal at http://<pi-ip>:8789/portal
```

## Grafana embed

Add a **Text** panel (HTML mode) or use an iframe pointing at
`http://192.168.1.189:8789/portal`. Because the page is served same-origin from
this service (not inlined into Grafana), its JavaScript and new-tab links behave
normally.
