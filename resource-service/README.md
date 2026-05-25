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
| `GET`  | `/`        | Redirects to `/vault` |
| `GET`  | `/vault`   | **The Vault** — cinematic entry + module grid (the deep-layer shell) |
| `GET`  | `/portal`  | The Sovereign Resource Portal page (latest `command-center-portal/portal.html` from GitHub `main`, with an offline fallback notice) |
| `GET`  | `/theater` | The Media Theater page — your saved Library + player + archive search |
| `GET`  | `/api/vault` | List saved resources (the Library) |
| `POST` | `/api/vault` | Save a resource (deduped by URL / archive.org identifier) |
| `DELETE` | `/api/vault/{id}` | Remove a saved resource |
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

## The Vault shell (`/vault`)

The deep-layer entry: a cinematic landing with large module panels. Grafana
stays the tactical *surface* dashboard; a "Vault" panel deep-links here into a
separate immersive app. Built dependency-free (one HTML file, served from GitHub
like the other pages) for generational recoverability.

Live modules open *inside* the Vault in an immersive full-screen stage
(`embed` mode); apps that refuse framing open in a new tab (`tab` mode). The
module registry is plain config at the top of `vault.html`, so targets/ports are
trivial to edit and recover.

| Module | Status | Target |
|--------|--------|--------|
| Library | live | embeds `/portal` (Resource Portal lives inside the Library) |
| Media Theater | live | embeds `/theater` |
| Art Studio | soon | `/studio` (next build — touch finger-painting) |
| Financial Cockpit | live | wallet-service `/console` |
| Family Archive | soon | Immich, later |
| Research Lab | soon | Jupyter / local tooling, later |
| Operational Console | live | Grafana (tab) |

## Resource Vault data (the saved Library)

Saved resources persist in a flat JSON array at `RESOURCE_DATA_PATH/vault.json`
on the Seagate (same pattern as the radio library), so the Library survives
container rebuilds and is shared across every device on the LAN/tailnet. Items
are deduped by archive.org identifier or URL, capped at 2000, and size-limited
per field. Anything can be saved — links *or* media:

| `type` | meaning | Library action |
|--------|---------|----------------|
| `link` | a resource URL (book, tool, docs) | **Open ↗** |
| `media-archive` | an archive.org item (has `identifier` + `media`) | **▶ Play** (resolved on demand) |
| `media-direct` | a direct media file URL | **▶ Play** |

The **Portal** writes `link` items via the `+` on each tile; the **Theater**'s
Find & Add tab writes `media-archive` items from search results (and
`media-direct` from the advanced URL box).

## Media Theater (`/theater`)

Now a two-tab page:

- **My Library** — your saved resources (`GET /api/vault`), filterable by
  All / Video / Audio / Links, each with Play or Open + Remove.
- **Find & Add** — Internet Archive search + in-page playback, resolved
  client-side via archive.org's public API (`advancedsearch.php` →
  `metadata/<id>` → `download/<id>/<file>`, the same flow the radio uses — no API
  key, no proxy). Tap a result to play; tap `+` to save it to the Library. Picks
  the best web-playable container (MP4/WebM/OGV for video, MP3/OGG for audio),
  with a fullscreen button and an advanced direct-URL play/save box.

Legal-by-construction: only public-domain / Creative-Commons archive content and
user-supplied URLs.

> The Grafana iframe embedding `/theater` should include `allow="fullscreen"`
> so the fullscreen button works inside the panel.

## Roadmap (not yet built)

- Link-health checks (flag dead saved links) and truthful downloaded/backed-up
  status by inspecting the external drive.
- Notes / tags / "legacy" flag on saved items.

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
