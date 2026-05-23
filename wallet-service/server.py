"""
Sovereignty Stack Wallet Service.

Phase 1: encrypted keystore + creation flow.
Phase 2.0: unlock/lock + 5-min idle session + chain registry (Mainnet, Base)
  + balance + ETH/USD price.

The private key never leaves this process. The keystore on disk is encrypted
with an Argon2id-derived AES-256-GCM key. While unlocked, the decrypted
mnemonic lives in an in-memory session entry that auto-expires after 5
minutes of idle (any session use resets the timer).

All crypto comes from well-known libraries:
  - argon2-cffi (RFC 9106 Argon2id)
  - cryptography (AES-256-GCM)
  - eth-account (BIP-39 / BIP-32 / BIP-44, the same library used by Brownie,
    Ape, web3.py)
No custom crypto. No hashlib for security purposes.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from eth_account import Account
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

# Enable BIP-39 / BIP-32 / BIP-44 features. eth-account flags these as
# "unaudited" but they are widely used in production (Brownie, Ape, etc.).
Account.enable_unaudited_hdwallet_features()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("wallet-service")

DATA_PATH = Path(os.getenv("WALLET_DATA_PATH", "/data"))
BACKUP_PATH = Path(os.getenv("WALLET_BACKUP_PATH", "/backup"))
KEYSTORE_FILENAME = "keystore.json"
AUDIT_FILENAME = "audit.log"

CONSOLE_URL = os.getenv(
    "WALLET_CONSOLE_URL",
    "https://raw.githubusercontent.com/Jdoink/sovereignty_stack/main/command-center-web3/console.html",
)

# Argon2id parameters. Tuned for a Pi 5: ~64 MB / 3 iterations / 4 threads.
# These are the values written into the keystore so decryption stays
# deterministic even if we tune defaults later.
ARGON2_TIME_COST = 3
ARGON2_MEMORY_COST = 64 * 1024  # 64 MiB
ARGON2_PARALLELISM = 4
ARGON2_HASH_LEN = 32  # 256-bit key for AES-256-GCM
ARGON2_SALT_LEN = 16
AES_NONCE_LEN = 12

KEYSTORE_VERSION = 1


# ============================================================================
# Crypto helpers
# ============================================================================
def derive_key(passphrase: str, salt: bytes) -> bytes:
    """Argon2id KDF -> AES-256 key."""
    return hash_secret_raw(
        secret=passphrase.encode("utf-8"),
        salt=salt,
        time_cost=ARGON2_TIME_COST,
        memory_cost=ARGON2_MEMORY_COST,
        parallelism=ARGON2_PARALLELISM,
        hash_len=ARGON2_HASH_LEN,
        type=Type.ID,
    )


def encrypt_with_passphrase(plaintext: bytes, passphrase: str) -> Dict[str, Any]:
    """Encrypt plaintext bytes with a passphrase. Returns a portable dict."""
    salt = secrets.token_bytes(ARGON2_SALT_LEN)
    nonce = secrets.token_bytes(AES_NONCE_LEN)
    key = derive_key(passphrase, salt)
    try:
        ciphertext = AESGCM(key).encrypt(nonce, plaintext, None)
    finally:
        # Best-effort zeroize. Python doesn't truly let us wipe bytes, but
        # rebinding the name removes the reference. The interpreter may keep
        # a copy in private buffers; we accept this in Phase 1.
        del key
    return {
        "version": KEYSTORE_VERSION,
        "kdf": "argon2id",
        "kdf_params": {
            "time_cost": ARGON2_TIME_COST,
            "memory_cost": ARGON2_MEMORY_COST,
            "parallelism": ARGON2_PARALLELISM,
            "hash_len": ARGON2_HASH_LEN,
        },
        "cipher": "aes-256-gcm",
        "salt": salt.hex(),
        "nonce": nonce.hex(),
        "ciphertext": ciphertext.hex(),
    }


def decrypt_with_passphrase(blob: Dict[str, Any], passphrase: str) -> bytes:
    """Mirror of encrypt_with_passphrase. Raises on bad passphrase / tampering."""
    if blob.get("version") != KEYSTORE_VERSION:
        raise ValueError(f"unsupported keystore version: {blob.get('version')}")
    if blob.get("kdf") != "argon2id" or blob.get("cipher") != "aes-256-gcm":
        raise ValueError("unsupported kdf or cipher")
    p = blob["kdf_params"]
    salt = bytes.fromhex(blob["salt"])
    nonce = bytes.fromhex(blob["nonce"])
    ciphertext = bytes.fromhex(blob["ciphertext"])
    key = hash_secret_raw(
        secret=passphrase.encode("utf-8"),
        salt=salt,
        time_cost=p["time_cost"],
        memory_cost=p["memory_cost"],
        parallelism=p["parallelism"],
        hash_len=p["hash_len"],
        type=Type.ID,
    )
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, None)
    finally:
        del key


# ============================================================================
# Keystore storage (Seagate primary + SD backup)
# ============================================================================
def keystore_paths() -> Dict[str, Path]:
    return {
        "primary": DATA_PATH / KEYSTORE_FILENAME,
        "backup": BACKUP_PATH / KEYSTORE_FILENAME,
    }


def keystore_exists() -> bool:
    return keystore_paths()["primary"].exists()


def load_keystore() -> Dict[str, Any]:
    p = keystore_paths()["primary"]
    if not p.exists():
        # Try backup if primary is missing.
        b = keystore_paths()["backup"]
        if b.exists():
            logger.warning("primary keystore missing; using backup at %s", b)
            return json.loads(b.read_text())
        raise FileNotFoundError("no keystore on primary or backup")
    return json.loads(p.read_text())


def save_keystore(data: Dict[str, Any]) -> None:
    """Atomically write to primary, then mirror to backup."""
    payload = json.dumps(data, indent=2)

    for label, path in keystore_paths().items():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(payload)
            tmp.replace(path)
            logger.info("wrote keystore (%s) at %s", label, path)
        except Exception:
            # Backup failure shouldn't block primary. Log loudly.
            logger.exception("failed to write %s keystore at %s", label, path)
            if label == "primary":
                raise


# ============================================================================
# Audit log (append-only on Seagate)
# ============================================================================
def audit(event: str, **details: Any) -> None:
    """Append a JSONL line. Best-effort - never raises into a request handler."""
    try:
        DATA_PATH.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
            "event": event,
            **details,
        }
        with (DATA_PATH / AUDIT_FILENAME).open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        logger.exception("audit log failure (event=%s)", event)


# ============================================================================
# Chain registry
# ============================================================================
# Multiple public RPCs per chain. rpc_call() tries them in order until one
# answers; this protects us from any single provider going down.
# Override with WALLET_RPC_MAINNET / WALLET_RPC_BASE (comma-separated list).
def _rpc_list(env_name: str, defaults: list) -> list:
    raw = (os.getenv(env_name) or "").strip()
    if raw:
        return [u.strip() for u in raw.split(",") if u.strip()]
    return defaults


CHAINS: Dict[int, Dict[str, Any]] = {
    1: {
        "name": "Ethereum",
        "symbol": "ETH",
        "rpc_urls": _rpc_list("WALLET_RPC_MAINNET", [
            "https://eth.llamarpc.com",
            "https://ethereum-rpc.publicnode.com",
            "https://rpc.ankr.com/eth",
        ]),
        "explorer": "https://etherscan.io",
    },
    8453: {
        "name": "Base",
        "symbol": "ETH",
        "rpc_urls": _rpc_list("WALLET_RPC_BASE", [
            "https://mainnet.base.org",
            "https://base-rpc.publicnode.com",
            "https://base.llamarpc.com",
        ]),
        "explorer": "https://basescan.org",
    },
}


async def rpc_call(chain_id: int, method: str, params: list) -> Any:
    """Minimal JSON-RPC client over httpx. Tries each configured RPC for the
    chain in order; returns the first success. Raises 502 if all fail."""
    chain = CHAINS.get(chain_id)
    if not chain:
        raise HTTPException(status_code=400, detail=f"unsupported chain {chain_id}")
    if http_client is None:
        raise HTTPException(status_code=503, detail="http client not initialized")
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}

    last_err: Any = None
    for url in chain["rpc_urls"]:
        try:
            r = await http_client.post(url, json=payload, timeout=8.0)
            r.raise_for_status()
            j = r.json()
            if "error" in j and j["error"] is not None:
                last_err = j["error"]
                logger.warning("rpc %s returned error: %s", url, j["error"])
                continue
            return j.get("result")
        except httpx.HTTPError as e:
            last_err = str(e)
            logger.warning("rpc %s transport error: %s", url, e)
            continue
        except Exception as e:
            last_err = str(e)
            logger.warning("rpc %s unexpected error: %s", url, e)
            continue
    raise HTTPException(
        status_code=502,
        detail=f"all RPCs failed for chain {chain_id}: {last_err}",
    )


# ============================================================================
# ETH/USD price (CoinGecko free API, 60s cache)
# ============================================================================
_price_cache: Dict[str, Any] = {"ts": 0.0, "value": None}


async def get_eth_usd_price() -> Optional[float]:
    now = time.time()
    if _price_cache["value"] is not None and (now - _price_cache["ts"]) < 60.0:
        return _price_cache["value"]
    if http_client is None:
        return _price_cache["value"]
    try:
        r = await http_client.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "ethereum", "vs_currencies": "usd"},
            timeout=6.0,
        )
        r.raise_for_status()
        price = float(r.json()["ethereum"]["usd"])
        _price_cache["ts"] = now
        _price_cache["value"] = price
        return price
    except Exception:
        logger.warning("eth/usd price fetch failed; returning cached value")
        return _price_cache["value"]


# ============================================================================
# Session management (in-memory, 5-min idle)
# ============================================================================
SESSION_TTL_SECONDS = 300

# token -> {"mnemonic": bytes, "address": str, "expires_at": float}
_sessions: Dict[str, Dict[str, Any]] = {}


def _zeroize(b: bytes) -> None:
    """Best-effort wipe. Python doesn't truly let us wipe immutable bytes, but
    we can overwrite a mutable view if the original was a bytearray."""
    try:
        if isinstance(b, bytearray):
            for i in range(len(b)):
                b[i] = 0
    except Exception:
        pass


def zeroize_session(token: str) -> None:
    s = _sessions.pop(token, None)
    if s is None:
        return
    mnemonic = s.get("mnemonic")
    if isinstance(mnemonic, (bytes, bytearray)):
        _zeroize(bytearray(mnemonic) if isinstance(mnemonic, bytes) else mnemonic)
    s["mnemonic"] = b""


def touch_session(token: str) -> Optional[Dict[str, Any]]:
    """Return the session if valid, resetting its TTL. None if expired/missing."""
    s = _sessions.get(token)
    if s is None:
        return None
    now = time.time()
    if s["expires_at"] < now:
        zeroize_session(token)
        audit("session.expire", token_prefix=token[:8])
        return None
    s["expires_at"] = now + SESSION_TTL_SECONDS
    return s


async def session_sweep() -> None:
    """Background task: every 30s, zeroize expired sessions."""
    while True:
        try:
            await asyncio.sleep(30)
            now = time.time()
            expired = [t for t, s in _sessions.items() if s["expires_at"] < now]
            for t in expired:
                zeroize_session(t)
                audit("session.expire", token_prefix=t[:8])
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("session_sweep failure (continuing)")


# ============================================================================
# FastAPI app
# ============================================================================
http_client: Optional[httpx.AsyncClient] = None
_sweep_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global http_client, _sweep_task
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(8.0))
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    BACKUP_PATH.mkdir(parents=True, exist_ok=True)
    _sweep_task = asyncio.create_task(session_sweep())
    logger.info(
        "wallet-service ready; data=%s backup=%s chains=%s",
        DATA_PATH, BACKUP_PATH, list(CHAINS.keys()),
    )
    try:
        yield
    finally:
        if _sweep_task is not None:
            _sweep_task.cancel()
        # Best-effort: zeroize all active sessions on shutdown.
        for token in list(_sessions.keys()):
            zeroize_session(token)
        if http_client is not None:
            await http_client.aclose()


app = FastAPI(
    title="Sovereignty Stack Wallet Service",
    version="0.1.0",
    description="Phase 1: encrypted keystore creation + console hosting.",
    lifespan=lifespan,
)


# ----- API models -----
class CreateRequest(BaseModel):
    passphrase: str = Field(min_length=8, max_length=512)


class CreateResponse(BaseModel):
    address: str
    mnemonic: str
    words: list[str]
    note: str


class StatusResponse(BaseModel):
    initialized: bool
    address: Optional[str]
    keystore_path: str
    backup_path: str
    backup_present: bool


# ----- API endpoints -----
@app.get("/api/health")
async def health() -> Dict[str, str]:
    return {"status": "ok", "phase": "1"}


@app.get("/api/wallet/status", response_model=StatusResponse)
async def status() -> StatusResponse:
    paths = keystore_paths()
    addr = None
    if paths["primary"].exists():
        try:
            addr = load_keystore().get("address")
        except Exception:
            logger.exception("failed to read keystore for status")
    return StatusResponse(
        initialized=paths["primary"].exists(),
        address=addr,
        keystore_path=str(paths["primary"]),
        backup_path=str(paths["backup"]),
        backup_present=paths["backup"].exists(),
    )


@app.post("/api/wallet/create", response_model=CreateResponse)
async def create_wallet(body: CreateRequest) -> CreateResponse:
    """
    Generate a fresh BIP-39 (24-word) wallet, encrypt the mnemonic with the
    user's passphrase, write to Seagate + SD, and return the mnemonic ONCE.

    After this response is sent, the mnemonic only exists encrypted on disk.
    The client is responsible for displaying it to the user with a confirm
    step and then clearing it from their view.
    """
    if keystore_exists():
        raise HTTPException(
            status_code=409,
            detail="wallet already initialized; refusing to overwrite",
        )

    # Generate a 24-word mnemonic + first account at the standard ETH path.
    account, mnemonic = Account.create_with_mnemonic(num_words=24)
    address = account.address
    # Throw away the in-memory key object. We only persist the (encrypted)
    # mnemonic. Future signing endpoints will decrypt the mnemonic and
    # re-derive the account on demand.
    del account

    # Encrypt the mnemonic string with the passphrase.
    blob = encrypt_with_passphrase(mnemonic.encode("utf-8"), body.passphrase)

    keystore = {
        "version": KEYSTORE_VERSION,
        "address": address,
        "derivation_path": "m/44'/60'/0'/0/0",
        "created_at": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "encrypted_mnemonic": blob,
    }
    save_keystore(keystore)
    audit("wallet.create", address=address)

    return CreateResponse(
        address=address,
        mnemonic=mnemonic,
        words=mnemonic.split(),
        note=(
            "This 24-word phrase is shown ONCE. Write it down on paper or "
            "metal NOW. With it you can restore this wallet on any device, "
            "even without the encrypted file or your passphrase. Anyone who "
            "sees it can drain this wallet."
        ),
    )


# ----- Phase 2.0: unlock / lock / session / chains / balance -----
class UnlockRequest(BaseModel):
    passphrase: str = Field(min_length=1, max_length=512)


class UnlockResponse(BaseModel):
    session_token: str
    expires_at: float
    ttl_seconds: int
    address: str


class LockRequest(BaseModel):
    session_token: str


@app.post("/api/wallet/unlock", response_model=UnlockResponse)
async def unlock_wallet(body: UnlockRequest) -> UnlockResponse:
    if not keystore_exists():
        raise HTTPException(status_code=404, detail="no wallet initialized")
    try:
        keystore = load_keystore()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"keystore load failed: {e}")

    try:
        mnemonic_bytes = decrypt_with_passphrase(
            keystore["encrypted_mnemonic"], body.passphrase
        )
    except Exception:
        audit("wallet.unlock.fail", address=keystore.get("address"))
        # Don't leak whether the keystore was corrupted vs wrong passphrase;
        # AES-GCM auth failure looks the same to the caller either way.
        raise HTTPException(status_code=401, detail="incorrect passphrase")

    token = secrets.token_urlsafe(32)
    now = time.time()
    expires_at = now + SESSION_TTL_SECONDS
    _sessions[token] = {
        "mnemonic": mnemonic_bytes,
        "address": keystore["address"],
        "expires_at": expires_at,
    }
    audit("wallet.unlock.ok", address=keystore["address"], token_prefix=token[:8])
    return UnlockResponse(
        session_token=token,
        expires_at=expires_at,
        ttl_seconds=SESSION_TTL_SECONDS,
        address=keystore["address"],
    )


@app.post("/api/wallet/lock")
async def lock_wallet(body: LockRequest) -> Dict[str, Any]:
    had = body.session_token in _sessions
    zeroize_session(body.session_token)
    if had:
        audit("wallet.lock", token_prefix=body.session_token[:8])
    return {"ok": True}


@app.get("/api/wallet/session")
async def session_info(token: str) -> Dict[str, Any]:
    s = touch_session(token)
    if s is None:
        return {"unlocked": False}
    now = time.time()
    return {
        "unlocked": True,
        "address": s["address"],
        "expires_at": s["expires_at"],
        "ttl_remaining": int(s["expires_at"] - now),
        "ttl_seconds": SESSION_TTL_SECONDS,
    }


@app.get("/api/chains")
async def list_chains() -> list:
    return [
        {
            "chain_id": cid,
            "name": c["name"],
            "symbol": c["symbol"],
            "explorer": c["explorer"],
        }
        for cid, c in CHAINS.items()
    ]


@app.get("/api/wallet/balance")
async def get_balance(chain_id: int, address: str) -> Dict[str, Any]:
    """Native balance for any address on a supported chain. No auth: balances
    are public on-chain data and we never expose the private key here."""
    if chain_id not in CHAINS:
        raise HTTPException(status_code=400, detail=f"unsupported chain {chain_id}")
    # Defensive address shape check (the RPC will reject malformed too, but a
    # 400 from us is friendlier than a 502).
    if not (isinstance(address, str) and address.startswith("0x") and len(address) == 42):
        raise HTTPException(status_code=400, detail="invalid address")

    chain = CHAINS[chain_id]
    balance_hex = await rpc_call(chain_id, "eth_getBalance", [address, "latest"])
    balance_wei = int(balance_hex, 16)
    balance_native = balance_wei / 10**18
    price = await get_eth_usd_price()
    usd_value = (balance_native * price) if price else None
    return {
        "chain_id": chain_id,
        "chain_name": chain["name"],
        "symbol": chain["symbol"],
        "explorer": chain["explorer"],
        "address": address,
        "balance_wei": str(balance_wei),
        "balance_native": balance_native,
        "usd_per_native": price,
        "usd_value": usd_value,
    }


# ----- Console hosting (so the UI is same-origin with the API) -----
@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse(url="/console", status_code=302)


@app.get("/console", response_class=HTMLResponse, include_in_schema=False)
async def console() -> HTMLResponse:
    """
    Always serve the latest console.html from GitHub main. If GitHub is
    unreachable, return a small fallback page so the user knows what to do.
    """
    if http_client is not None:
        try:
            r = await http_client.get(CONSOLE_URL)
            if r.status_code == 200 and r.text:
                return HTMLResponse(
                    content=r.text,
                    headers={"Cache-Control": "no-store, max-age=0"},
                )
        except Exception:
            logger.exception("failed to fetch console from %s", CONSOLE_URL)

    fallback = (
        "<!doctype html><meta charset='utf-8'>"
        "<title>Wallet Console</title>"
        "<body style='font-family:system-ui;background:#05070a;color:#d4dde4;"
        "padding:24px'>"
        "<h2 style='color:#5ad3ff'>Wallet console unavailable</h2>"
        f"<p>Could not fetch console from <code>{CONSOLE_URL}</code>.</p>"
        "<p>The API is still running at <code>/api/wallet/status</code>.</p>"
        "</body>"
    )
    return HTMLResponse(content=fallback, status_code=503)
