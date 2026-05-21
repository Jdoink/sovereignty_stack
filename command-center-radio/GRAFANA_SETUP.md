# Command Center Radio — Grafana setup (iframe edition)

After we discovered that the Business Text plugin's sanitizer in your build strips inline `<style>` blocks and event handlers, the radio is now served as a self-contained page by **`ticker-service`** and embedded in Grafana via a single `<iframe>` tag.

The radio lives at `GET /radio` on the ticker-service. The Grafana panel becomes a window onto it — full CSS, full JS, dropdown UI, visualizer, all running inside the iframe where nothing can sanitize them.

---

## 1. Update the ticker-service container

The new endpoint is in `ticker-service/server.py`. To pick it up:

```bash
cd /path/to/sovereignty_stack/ticker-service
git pull
# In Dockge: open the ticker-service stack, click "Update".
# Or via CLI:
docker compose up -d --build
```

Verify it's live:

```bash
curl -I http://192.168.1.189:8787/radio
# HTTP/1.1 200 OK
# content-type: text/html; charset=utf-8
```

You can also open `http://192.168.1.189:8787/radio` directly in a browser to test the radio outside of Grafana. The dropdown, play/pause, volume, and visualizer should all work there before you touch Grafana.

---

## 2. Wire it into Grafana

1. Edit your Command Center panel (or add a new one). Visualization: **Business Text**.
2. **Default Content** field, HTML mode, paste **exactly this one line**:

```html
<iframe src="http://192.168.1.189:8787/radio" style="width:100%;height:100%;border:0;display:block;background:#05070a" allow="autoplay" loading="eager"></iframe>
```

3. **Leave CSS Styles → URL empty.** Leave every JavaScript hook empty. Leave Content Partials empty.
4. Click outside the editor → **Save** → **Back to dashboard**.

That's it. The radio should now render inside the panel and be fully interactive.

---

## 3. Sizing tips

- The iframe stretches to fill the Business Text panel via `width:100%;height:100%`. Resize the panel in Grafana like any other and the radio scales with it.
- The radio internally uses `clamp()` and grid layouts, so it looks right anywhere from ~280px wide up to a full-screen kiosk.
- For best aesthetics, give the panel at least 6 grid units of height (≈ 300px) so the visualizer has room to breathe.

---

## 4. Notes

- **Autoplay**: Modern browsers require a user gesture before audio plays. Clicking PLAY or selecting a station from the dropdown counts as the gesture, so the first interaction always works. The `allow="autoplay"` on the iframe is there for completeness — it doesn't bypass the gesture requirement, but it does prevent some browsers from being extra-strict about iframed audio.
- **Mixed content**: If Grafana is served over HTTPS but the ticker-service over HTTP, browsers will block the iframe (mixed content). Either put both behind the same reverse proxy with TLS, or access Grafana over HTTP on the LAN. Currently both are LAN HTTP, so this is fine.
- **CORS / Visualizer**: The visualizer reaches out to SomaFM with `crossOrigin = "anonymous"`. SomaFM's `ice2` host serves the right headers. If you ever add a station whose origin doesn't, the VIZ button will report `BLOCKED` and playback continues normally.
- **Adding stations**: Edit the `STATIONS` array in `ticker-service/server.py` (inside `RADIO_HTML`). Rebuild the container. The dropdown updates automatically.

---

## 5. Why we switched from inline HTML to iframe

The earlier attempts (`content.html`, `all-in-one.html`) assumed the Business Text plugin would honor `<style>` blocks and inline event handlers. Your plugin build sanitizes both — the HTML rendered but the styling and JS were stripped, which is why clicks did nothing and the layout was unstyled.

The iframe sidesteps sanitization entirely. The plugin sees a single `<iframe>` element, which it leaves alone. Inside the iframe is a normal browser document with no sanitization, so our CSS and JS run as written.

The files `content.html`, `styles.css`, `after-content-ready.js`, and `all-in-one.html` are kept in the repo in case you ever land on a plugin version that exposes proper JS hooks and you want the "clean" version. For your current build, **use the iframe approach only**.
