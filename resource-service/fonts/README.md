# Vault fonts (self-hosted, optional)

The Vault uses **Cinzel** (Roman-capital titles) and **Cormorant** (old-world
body serif). Both are open-source (OFL). They're served locally from this
directory at `/fonts/...` — no Google/CDN dependency at runtime.

Until the files are present, the Vault falls back to a web-safe classical stack
(Palatino / Optima / Georgia), so it still looks the part. Drop the files in to
get the true engraved-marble look.

## How to add them (run on the Pi)

Download each family from <https://fonts.google.com> (Cinzel, Cormorant) — click
**Get font → Download all**, unzip, and copy a `.ttf` (or `.woff2`) into this
folder named exactly:

```
resource-service/fonts/cinzel.ttf        (or cinzel.woff2)
resource-service/fonts/cormorant.ttf     (or cormorant.woff2)
```

The `@font-face` rules accept either `.woff2` or `.ttf`.

Then rebuild so they're baked into the image, and commit them for recoverability:

```bash
cd ~/sovereignty_stack/resource-service
docker compose up -d --build
git add fonts/cinzel.* fonts/cormorant.* && git commit -m "Add Vault fonts" && git push
```

(`.woff2` is smaller and preferred; `.ttf` works fine too.)
