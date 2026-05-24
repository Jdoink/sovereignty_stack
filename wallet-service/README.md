# Wallet Service

A Pi-hosted, LAN-only Ethereum keystore service. Phase 1: create an encrypted wallet and serve the console UI.

## What it does today (Phase 1)

- Generates a fresh BIP-39 (24-word) Ethereum wallet on the Pi.
- Encrypts the mnemonic with Argon2id (RFC 9106) + AES-256-GCM using a passphrase you choose.
- Writes the encrypted keystore to **two** locations atomically: the Seagate (primary) and the Pi SD card (backup).
- Returns the mnemonic phrase **exactly once** during creation. You must write it down on paper or metal at that moment.
- Serves `/console` — the latest Web3 Console UI from GitHub — so the browser is same-origin with the wallet API (no mixed-content, no CORS gymnastics).

## What it does NOT do yet

- Signing (Phase 2)
- Allowlist + Tenderly simulation gate (Phase 3)
- Safe multisig integration (Phase 4)
- YubiKey-based unlock (Phase 5)

No private key ever leaves this process. No network egress except to GitHub (for the console HTML) and outbound RPCs in later phases.

## Architecture

```
Browser (LAN) ──HTTP──> wallet-service @ Pi:8788
                         ├── /console     -> proxies latest console.html
                         ├── /api/wallet/* -> wallet operations
                         ├── /data        -> Seagate keystore + audit log
                         └── /backup      -> SD-card mirror of keystore
```

## Setup

### 1. Make the directories

On the Pi (via Filebrowser or any shell):

```
/media/devmon/sda1-usb-Seagate_BUP_Slim/sovereignty-stack/wallet   # primary
/var/lib/wallet-service-backup                                     # SD backup
```

### 2. Build and run

```bash
cd ~/sovereignty_stack/wallet-service
docker compose up -d --build
```

Then check:

```bash
curl http://192.168.1.189:8788/api/health
# {"status":"ok","phase":"1"}

curl http://192.168.1.189:8788/api/wallet/status
# {"initialized":false,...}
```

### 3. Switch the Grafana iframe

Update your Web3 panel's iframe to point at the Pi (same pattern as `/radio`):

```html
<iframe src="http://192.168.1.189:8788/console" width="100%" height="540" style="border:0;display:block" allow="popups"></iframe>
```

The console then auto-detects it's running same-origin with the wallet API and reveals the `WALLET` tab. If you keep the CDN URL, the `WALLET` tab will show a "service unreachable" message because of HTTPS-to-HTTP mixed content blocking.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/api/health` | Liveness check |
| `GET`  | `/api/wallet/status` | Is a wallet initialized? What's its address? |
| `POST` | `/api/wallet/create` | Generate a new wallet (passphrase in JSON body). Returns the mnemonic exactly once. |
| `GET`  | `/console` | Serves the latest console.html from GitHub main |
| `GET`/`POST`/`DELETE` | `/api/tokens/custom` | User-saved token directory (persisted to Seagate + SD). POST resolves symbol/decimals on-chain and saves; the swap dropdowns read from it. |

### Aerodrome (Base) direct actions

Swap, lock (veAERO), vote, and claim rewards directly against Aerodrome's
audited contracts on Base — no WalletConnect, no dApp browser. Every action only
*builds* calldata; signing + broadcasting still flow through `/api/tx/send`, so
the same review + simulation gate applies. The complex ABI encoding (Route
structs, weight arrays) is done in Python with `eth_abi`, not hand-rolled in JS.

| Method | Path | Purpose |
|---|---|---|
| `GET`  | `/api/defi/aerodrome/info` | Contract registry + curated swap tokens for the chain |
| `GET`  | `/api/defi/aerodrome/locks` | List an address's veAERO locks (amount, unlock, claimable rebase) |
| `GET`  | `/api/defi/aerodrome/allowance` | ERC20 allowance for a spender (used to decide if an approve is needed) |
| `POST` | `/api/defi/aerodrome/quote` | Best swap route across candidates via `getAmountsOut` |
| `POST` | `/api/defi/aerodrome/reward-info` | Derive a pool's gauge + fee/bribe reward contracts and reward tokens |
| `POST` | `/api/defi/aerodrome/build` | Build `{to, value_wei, data}` for an action (swap / lock / vote / claim) |

## Threat model honesty

Phase 1 is **passphrase-only** (Tier 2 in our planning doc). It protects against:

- Lost Pi (encrypted file is useless without your passphrase)
- Casual remote attacker (no plaintext key on disk)
- Phishing / blind-sign attacks (signing UI is yours, not the dApp's — even though signing itself is Phase 2)
- Main-computer compromise (key never lived there)

It does **not** protect against:

- An attacker with root on the Pi during an active signing window (they can read the decrypted mnemonic from RAM)
- A keylogger watching you type the passphrase

Mitigations: keep the Pi up to date, no untrusted SSH access, minimal exposed services. We'll add YubiKey-based unlock in Phase 5 (Tier 3) which closes the "encrypted file alone is enough" gap.

## Backups

You should end up with three copies of recovery material after setup:

1. **Encrypted keystore on the Seagate** (`/media/.../sovereignty-stack/wallet/keystore.json`)
2. **Encrypted keystore on the SD card** (`/var/lib/wallet-service-backup/keystore.json`)
3. **Paper / metal copy of the 24-word seed phrase**

Any one of them plus your passphrase (or the seed phrase alone) is enough to fully restore the wallet.

## Stack

| Component | Library | Why |
|---|---|---|
| Web framework | FastAPI | Same as `ticker-service` |
| KDF | `argon2-cffi` | RFC 9106 standard |
| Encryption | `cryptography` (AES-256-GCM) | Python reference crypto lib |
| Wallet primitives | `eth-account` | Used by Brownie / Ape / web3.py |
| HTTP client | `httpx` | For serving the console |

No custom crypto. If you ever see this codebase using `hashlib` for security purposes, that's a bug.
