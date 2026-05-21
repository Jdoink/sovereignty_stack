# Command Center Radio

A Grafana panel that turns the Business Text plugin (`volkovlabs-dynamictext-panel`) into a self-contained "audio subsystem" for the Sovereignty Stack dashboard.

No iframes. No Navidrome UI embed. No popup windows. One persistent `<audio>` element, JS-driven station switching, retro-futuristic Bloomberg/NORAD styling, and a CORS-aware visualizer scaffold for later.

---

## Why the previous Text-panel attempt was janky

The standard Grafana **Text** panel has two failure modes for this use case:

1. It renders Markdown/HTML but strips most JS, so `onclick` handlers either vanish or fall through to default browser behavior - which for `<a href="stream.mp3">` is "open in a new tab."
2. Each "button" was effectively a link, so every click navigated away instead of swapping the source on an existing player.

This panel fixes both by:

- using `<button type="button">` exclusively (no anchors, no `target="_blank"`),
- attaching all click handlers in the Business Text plugin's **After Content Ready** JavaScript hook (not inline), and
- keeping **one** `<audio id="cc-audio">` element alive for the lifetime of the panel and only mutating `audio.src`.

---

## Files

| File | Where it goes in the Business Text panel |
|---|---|
| `content.html` | **Content** field, mode = `HTML` |
| `styles.css` | **Styles** field |
| `after-content-ready.js` | **JavaScript Code** → **After Content Ready** |
| `stations.json` | Reference only - station registry to keep in sync with `content.html` |

---

## Setup

### 1. Install the plugin

You're already doing this. The Grafana env var:

```yaml
environment:
  GF_INSTALL_PLUGINS: volkovlabs-dynamictext-panel
```

If the panel does not appear in the visualization picker after a Grafana restart, also allow unsigned plugins (Volkov publishes signed builds, but pinning the ID belt-and-suspenders):

```yaml
environment:
  GF_INSTALL_PLUGINS: volkovlabs-dynamictext-panel
  GF_PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS: volkovlabs-dynamictext-panel
```

### 2. Create the panel

1. Add a new panel to your Command Center dashboard.
2. Choose visualization **Business Text** (a.k.a. Dynamic Text).
3. Data source: **`-- Dashboard --`** with no query, or **TestData DB** with a single empty series. The panel does not need data - it just needs to render the default content once.
4. **Content** tab → set **Content Type** = `HTML`, **Rendering Mode** = `Everytime` (or `Once` if available; both work because the panel has no data dependency). Paste `content.html`.
5. **Styles** tab → paste `styles.css`.
6. **JavaScript Code** tab → paste `after-content-ready.js` into the **After Content Ready** editor. Leave Before Render / On Init empty.
7. **Save dashboard.**

### 3. Disable panel auto-refresh

The audio element is recreated whenever the panel re-renders its HTML. To keep playback stable, set the dashboard refresh to **Off** (or set the panel's own refresh override to `Off` via panel options if exposed). Time range can stay whatever you want; it doesn't affect this panel.

### 4. Touchscreen tweaks (Pi 7" / kiosk)

- The buttons are sized at `min-height: 40px` and `min-height: 64px` (station tiles), which is past the 44px Apple/Google touch-target floor.
- `touch-action: manipulation` is set on every interactive element to kill the 300 ms tap delay.
- `user-select: none` and `-webkit-tap-highlight-color: transparent` are on the root so nothing flashes blue on tap.

---

## How it works (architecture)

```
                  ┌─────────────────────────────────────────┐
                  │           Business Text Panel            │
                  │                                          │
                  │   Content (HTML)  ──┐                    │
                  │   Styles (CSS)    ──┤                    │
                  │                     ▼                    │
                  │   <div id="cc-radio">                    │
                  │     <header/>                            │
                  │     <display + canvas/>                  │
                  │     <stations: <button data-station-url>>│
                  │     <controls: play/pause/stop/vol/viz>  │
                  │     <audio id="cc-audio"/>  ◀── single   │
                  │   </div>                                 │
                  │                                          │
                  │   After Content Ready (JS)               │
                  │     - query #cc-radio inside             │
                  │       context.element                    │
                  │     - bind handlers                      │
                  │     - manage state on root._ccState      │
                  └─────────────────────────────────────────┘
                                  │
                  station click ──┘
                                  │
                                  ▼
                  audio.src = url;  audio.load();  audio.play();
                                  │
                                  ▼  (opt-in)
                  AudioContext → AnalyserNode → <canvas>
```

Key invariants:

- **One `<audio>` element, ever.** Switching stations only mutates `src`. This is what makes the player "persistent."
- **No anchors, no inline handlers.** Every interactive element is `<button type="button">` and gets wired up in JS via `addEventListener`, with `event.preventDefault()` on every click. That's what kills the "opens a new window" behavior.
- **Idempotent init.** `root._ccInit` guards against the After Content Ready hook re-binding handlers if the plugin re-fires it.
- **Audio-event-driven UI.** Status pill and play/pause icon are updated from `audio` events (`playing`, `pause`, `waiting`, `stalled`, `error`), not from the click handler. So if the network drops mid-stream the UI tracks reality instead of lying.

---

## Adding stations

Edit `content.html` and add another `<button class="cc-station" …>` inside `#cc-stations`. The JS auto-discovers every `.cc-station` and reads `data-station-url` + `data-station-name`. Then mirror the entry in `stations.json` so the registry stays canonical.

**Stream URL rules** (from your existing Navidrome experience):

- Use **direct MP3 stream URLs** only. `.pls` and `.m3u` are playlists; the HTML5 `<audio>` element won't follow them.
- For SomaFM, the working pattern is `https://ice2.somafm.com/<station>-128-mp3`.
- HTTPS only. Grafana is served over HTTPS on most setups; mixed-content blocks would silently kill HTTP streams.

---

## Visualizer notes (CORS gotcha)

The visualizer is **opt-in** (VIZ button). It uses `AudioContext.createMediaElementSource()` and an `AnalyserNode`. There's a browser rule worth knowing about:

> If the `<audio>` element has cross-origin media and `crossOrigin` is not set to `"anonymous"` with valid CORS headers from the origin, `createMediaElementSource` either taints the output (silent audio) or throws.

This panel handles that by:

1. Only setting `audio.crossOrigin = 'anonymous'` when you click VIZ.
2. Re-loading the current `src` under the new CORS mode.
3. Falling back silently (VIZ shows `BLOCKED`) if the analyser can't be wired up - playback continues normally with no visualizer.

SomaFM's `ice2.somafm.com` serves the right CORS headers in practice, so VIZ should work for the four stations shipped here. If you add a station whose origin doesn't, VIZ will report `BLOCKED` for that station only.

---

## Future hooks (visualizer / ambient reactive modes)

`drawBars()` in `after-content-ready.js` is intentionally tiny and replaceable. To swap renderers, add a mode dropdown and branch inside the `requestAnimationFrame` loop. The `analyser` is already configured (`fftSize = 128`, time-domain or frequency data both available via `getByteTimeDomainData` / `getByteFrequencyData`).

Ideas that fit the aesthetic:

- **Oscilloscope** (time-domain trace) - swap to `getByteTimeDomainData` and draw a polyline.
- **NORAD threat-board** - eight LED-style level meters mapped to FFT bands.
- **Ambient reactive backdrop** - sample RMS energy and tint a CSS variable on `#cc-radio` so the panel background pulses with the music. Implementation hint: `root.style.setProperty('--cc-amber', …)` from the RAF loop.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Buttons open a new tab | You pasted an older version with `<a href>` tags, or the plugin sanitized your HTML. | Use `content.html` from this directory verbatim; verify the rendered DOM has `<button>` not `<a>`. |
| Click does nothing | After Content Ready JS not pasted, or pasted into the wrong hook (`Before Render` won't find the elements). | Re-paste into **After Content Ready**. Open browser devtools → check `document.querySelector('#cc-radio')._ccInit` is `true`. |
| Audio plays for a second then stops | Browser autoplay policy. First interaction must come from a user gesture. | Tap a station button. The current design always plays in response to a click, so this should not occur after the first interaction. |
| `BLOCKED` on VIZ button | Stream origin doesn't send CORS headers. | Either leave VIZ off for that station, or proxy the stream through your own server with `Access-Control-Allow-Origin: *`. |
| Player resets on dashboard refresh | The Business Text panel re-renders content on data refresh and recreates `<audio>`. | Set dashboard refresh to **Off** (or use the panel's "Render Once" mode if your plugin version exposes it). |
