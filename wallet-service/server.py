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


# ----- Phase 2.1: transaction estimate + sign + broadcast -----
class TxEstimateRequest(BaseModel):
    chain_id: int
    from_address: str = Field(..., alias="from")
    to: str
    # value_wei as a string to avoid JavaScript's Number precision loss at
    # >2^53. Same for max_fee_per_gas, max_priority_fee_per_gas on send.
    value_wei: str
    data: Optional[str] = "0x"

    model_config = {"populate_by_name": True}


class TxSendRequest(BaseModel):
    session_token: str
    chain_id: int
    to: str
    value_wei: str
    gas_limit: int
    max_fee_per_gas: str
    max_priority_fee_per_gas: str
    nonce: int
    data: Optional[str] = "0x"


def _validate_address(addr: str, label: str) -> None:
    if not (isinstance(addr, str) and addr.startswith("0x") and len(addr) == 42):
        raise HTTPException(status_code=400, detail=f"invalid {label} address")


def _hex_to_int(h: str) -> int:
    return int(h, 16) if isinstance(h, str) and h.startswith("0x") else int(h)


@app.post("/api/tx/estimate")
async def estimate_tx(body: TxEstimateRequest) -> Dict[str, Any]:
    """Estimate nonce, gas limit, and EIP-1559 fee suggestions for a tx.
    No private key access here - any caller can hit this; it's read-only RPC.
    """
    if body.chain_id not in CHAINS:
        raise HTTPException(status_code=400, detail=f"unsupported chain {body.chain_id}")
    _validate_address(body.from_address, "from")
    _validate_address(body.to, "to")
    try:
        value_wei = int(body.value_wei)
        if value_wei < 0:
            raise ValueError("negative")
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid value_wei")

    data_field = body.data or "0x"

    # --- Nonce (pending) ---
    nonce_hex = await rpc_call(body.chain_id, "eth_getTransactionCount",
                               [body.from_address, "pending"])
    nonce = _hex_to_int(nonce_hex)

    # --- Gas limit estimate ---
    # Plain ETH transfer is 21000. For others, ask the RPC. Fall back to a
    # generous default if estimateGas reverts (e.g. recipient is a contract
    # that will revert until certain state holds).
    try:
        gas_hex = await rpc_call(body.chain_id, "eth_estimateGas", [{
            "from": body.from_address,
            "to": body.to,
            "value": hex(value_wei),
            "data": data_field,
        }])
        gas_limit = _hex_to_int(gas_hex)
    except HTTPException:
        gas_limit = 21000 if data_field == "0x" else 100000

    # --- Fee suggestions via eth_feeHistory ---
    # Percentiles 25 / 50 / 75 give us slow / standard / fast priority fees.
    base_fee_per_gas = 0
    try:
        fh = await rpc_call(body.chain_id, "eth_feeHistory",
                            [hex(5), "latest", [25, 50, 75]])
        base_fees = [_hex_to_int(f) for f in fh["baseFeePerGas"]]
        # The last element is the predicted base fee for the next block.
        base_fee_per_gas = base_fees[-1]
        rewards = [[_hex_to_int(r) for r in blk] for blk in fh["reward"]]
        # Average across blocks per percentile
        n = max(len(rewards), 1)
        avg = [sum(blk[i] for blk in rewards) // n for i in range(3)]
        prio_slow, prio_std, prio_fast = avg[0], avg[1], avg[2]
    except Exception:
        logger.warning("eth_feeHistory failed; falling back to eth_gasPrice", exc_info=True)
        gp_hex = await rpc_call(body.chain_id, "eth_gasPrice", [])
        gp = _hex_to_int(gp_hex)
        base_fee_per_gas = gp
        prio_slow = max(gp // 10, 10**8)         # at least 0.1 gwei
        prio_std  = max(gp // 5,  10**9)         # at least 1 gwei
        prio_fast = max(gp // 3,  2 * 10**9)     # at least 2 gwei

    # Floor priority fees at 1 wei so RPCs that reject zero-priority are happy.
    prio_slow = max(prio_slow, 1)
    prio_std  = max(prio_std, 1)
    prio_fast = max(prio_fast, 1)

    def build(prio: int) -> Dict[str, str]:
        # max_fee = 2 * base + priority gives ~1 block of base-fee headroom.
        max_fee = base_fee_per_gas * 2 + prio
        return {
            "max_priority_fee_per_gas": str(prio),
            "max_fee_per_gas": str(max_fee),
        }

    fee_suggestions = {
        "slow":     build(prio_slow),
        "standard": build(prio_std),
        "fast":     build(prio_fast),
    }

    price = await get_eth_usd_price()
    estimated_cost = {}
    for name, fees in fee_suggestions.items():
        fee_wei = gas_limit * int(fees["max_fee_per_gas"])
        fee_native = fee_wei / 10**18
        estimated_cost[name] = {
            "fee_wei": str(fee_wei),
            "fee_native": fee_native,
            "fee_usd": (fee_native * price) if price else None,
        }

    return {
        "chain_id": body.chain_id,
        "nonce": nonce,
        "gas_limit": gas_limit,
        "base_fee_per_gas": str(base_fee_per_gas),
        "fee_suggestions": fee_suggestions,
        "estimated_cost": estimated_cost,
        "usd_per_native": price,
    }


@app.post("/api/tx/send")
async def send_tx(body: TxSendRequest) -> Dict[str, Any]:
    """Sign + broadcast a transaction. Requires a valid session."""
    s = touch_session(body.session_token)
    if s is None:
        raise HTTPException(status_code=401, detail="session expired or invalid")
    if body.chain_id not in CHAINS:
        raise HTTPException(status_code=400, detail=f"unsupported chain {body.chain_id}")
    _validate_address(body.to, "to")

    try:
        value_wei = int(body.value_wei)
        max_fee = int(body.max_fee_per_gas)
        max_priority = int(body.max_priority_fee_per_gas)
        if value_wei < 0 or max_fee < 0 or max_priority < 0:
            raise ValueError("negative")
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid numeric field")

    if max_priority > max_fee:
        raise HTTPException(
            status_code=400,
            detail="max_priority_fee_per_gas cannot exceed max_fee_per_gas",
        )
    if body.gas_limit < 21000:
        raise HTTPException(status_code=400, detail="gas_limit too low (min 21000)")

    # Derive the signing account from the (in-memory, decrypted) mnemonic.
    try:
        mnemonic_str = bytes(s["mnemonic"]).decode("utf-8")
    except Exception:
        raise HTTPException(status_code=500, detail="session mnemonic corrupt")
    acct = Account.from_mnemonic(mnemonic_str, account_path="m/44'/60'/0'/0/0")
    if acct.address.lower() != s["address"].lower():
        # Defense in depth: should never happen, but reject if mnemonic doesn't
        # derive the address we have on file.
        raise HTTPException(status_code=500, detail="derived address mismatch")

    tx = {
        "chainId": body.chain_id,
        "nonce": body.nonce,
        "to": body.to,
        "value": value_wei,
        "gas": body.gas_limit,
        "maxFeePerGas": max_fee,
        "maxPriorityFeePerGas": max_priority,
        "data": body.data or "0x",
        "type": 2,
    }

    audit("tx.send.attempt",
          chain_id=body.chain_id,
          from_addr=s["address"], to=body.to,
          value_wei=str(value_wei), nonce=body.nonce,
          gas_limit=body.gas_limit,
          max_fee=str(max_fee), max_priority=str(max_priority))

    try:
        signed = acct.sign_transaction(tx)
    except Exception as e:
        audit("tx.send.sign_fail", from_addr=s["address"], error=str(e))
        raise HTTPException(status_code=400, detail=f"signing failed: {e}")

    raw_bytes = getattr(signed, "raw_transaction", None) or getattr(signed, "rawTransaction", None)
    if raw_bytes is None:
        raise HTTPException(status_code=500, detail="signer returned no raw transaction")
    raw_hex = "0x" + raw_bytes.hex()

    try:
        tx_hash = await rpc_call(body.chain_id, "eth_sendRawTransaction", [raw_hex])
    except HTTPException as e:
        audit("tx.send.broadcast_fail",
              from_addr=s["address"], to=body.to,
              chain_id=body.chain_id, error=str(e.detail))
        raise

    audit("tx.send.ok",
          chain_id=body.chain_id,
          from_addr=s["address"], to=body.to,
          value_wei=str(value_wei), tx_hash=tx_hash)

    chain = CHAINS[body.chain_id]
    return {
        "tx_hash": tx_hash,
        "explorer_url": f"{chain['explorer']}/tx/{tx_hash}",
        "chain_id": body.chain_id,
    }


# ----- Phase 2.2: ERC20 token support -----
# Curated token list per chain. price_source: "stable" -> assume $1, "eth" ->
# use ETH/USD price, None -> don't show USD value.
CURATED_TOKENS: Dict[int, list] = {
    1: [
        {"address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "symbol": "USDC",
         "name": "USD Coin",        "decimals": 6,  "price_source": "stable"},
        {"address": "0xdAC17F958D2ee523a2206206994597C13D831ec7", "symbol": "USDT",
         "name": "Tether USD",      "decimals": 6,  "price_source": "stable"},
        {"address": "0x6B175474E89094C44Da98b954EedeAC495271d0F", "symbol": "DAI",
         "name": "Dai Stablecoin",  "decimals": 18, "price_source": "stable"},
        {"address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "symbol": "WETH",
         "name": "Wrapped Ether",   "decimals": 18, "price_source": "eth"},
        {"address": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599", "symbol": "WBTC",
         "name": "Wrapped BTC",     "decimals": 8,  "price_source": None},
    ],
    8453: [
        {"address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "symbol": "USDC",
         "name": "USD Coin",        "decimals": 6,  "price_source": "stable"},
        {"address": "0x4200000000000000000000000000000000000006", "symbol": "WETH",
         "name": "Wrapped Ether",   "decimals": 18, "price_source": "eth"},
        {"address": "0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22", "symbol": "cbETH",
         "name": "Coinbase Wrapped Staked ETH", "decimals": 18, "price_source": "eth"},
    ],
}

ERC20_SELECTORS = {
    "symbol":    "0x95d89b41",
    "name":      "0x06fdde03",
    "decimals":  "0x313ce567",
    "balanceOf": "0x70a08231",
    "transfer":  "0xa9059cbb",
}


def _encode_address_arg(addr: str) -> str:
    """Pad an address to 32 bytes (right-aligned, hex, no 0x)."""
    if not (isinstance(addr, str) and addr.startswith("0x") and len(addr) == 42):
        raise ValueError(f"invalid address: {addr}")
    return addr[2:].lower().zfill(64)


def _decode_abi_string(hex_data: str) -> str:
    """Decode an ABI-encoded string return value. Falls back to bytes32 for
    old tokens (MKR-style) that return fixed bytes instead of dynamic string."""
    h = (hex_data or "").replace("0x", "")
    if len(h) < 128:
        try:
            return bytes.fromhex(h).rstrip(b"\x00").decode("utf-8", errors="replace")
        except Exception:
            return ""
    try:
        offset = int(h[:64], 16) * 2
        length = int(h[offset:offset + 64], 16) * 2
        data = h[offset + 64:offset + 64 + length]
        return bytes.fromhex(data).decode("utf-8", errors="replace")
    except Exception:
        # Last resort: bytes32 interpretation
        try:
            return bytes.fromhex(h[:64]).rstrip(b"\x00").decode("utf-8", errors="replace")
        except Exception:
            return ""


def _decode_abi_uint(hex_data: str) -> int:
    h = (hex_data or "").replace("0x", "")
    return int(h, 16) if h else 0


@app.get("/api/tokens")
async def list_tokens(chain_id: int) -> list:
    if chain_id not in CHAINS:
        raise HTTPException(status_code=400, detail=f"unsupported chain {chain_id}")
    return CURATED_TOKENS.get(chain_id, [])


@app.get("/api/token/info")
async def token_info(chain_id: int, address: str) -> Dict[str, Any]:
    """Read symbol/name/decimals from a token contract. Used for custom tokens
    not in the curated list."""
    if chain_id not in CHAINS:
        raise HTTPException(status_code=400, detail=f"unsupported chain {chain_id}")
    _validate_address(address, "token")

    try:
        sym_hex = await rpc_call(chain_id, "eth_call",
                                 [{"to": address, "data": ERC20_SELECTORS["symbol"]}, "latest"])
        symbol = _decode_abi_string(sym_hex).strip()
    except Exception:
        symbol = ""
    try:
        name_hex = await rpc_call(chain_id, "eth_call",
                                  [{"to": address, "data": ERC20_SELECTORS["name"]}, "latest"])
        name = _decode_abi_string(name_hex).strip()
    except Exception:
        name = ""
    try:
        dec_hex = await rpc_call(chain_id, "eth_call",
                                 [{"to": address, "data": ERC20_SELECTORS["decimals"]}, "latest"])
        decimals = _decode_abi_uint(dec_hex)
    except Exception:
        decimals = -1

    if not symbol or not (0 <= decimals <= 36):
        raise HTTPException(
            status_code=400,
            detail="contract did not respond to ERC20 symbol()/decimals()",
        )

    return {
        "address": address,
        "symbol": symbol,
        "name": name or symbol,
        "decimals": decimals,
        "price_source": None,
    }


@app.get("/api/token/balance")
async def token_balance(chain_id: int, token: str, address: str) -> Dict[str, str]:
    if chain_id not in CHAINS:
        raise HTTPException(status_code=400, detail=f"unsupported chain {chain_id}")
    _validate_address(token, "token")
    _validate_address(address, "address")
    data = ERC20_SELECTORS["balanceOf"] + _encode_address_arg(address)
    result = await rpc_call(chain_id, "eth_call",
                            [{"to": token, "data": data}, "latest"])
    return {"balance_wei": str(_decode_abi_uint(result))}


# ----- Phase 2.3: safe contracts (curated, read-only) + contacts (CRUD) -----
# Curated list of well-known contracts per chain. Used by the review screen
# to label recipients ("Uniswap V3 SwapRouter" instead of just an address).
# Addresses are checksummed.
SAFE_CONTRACTS: Dict[int, list] = {
    1: [
        {"address": "0xE592427A0AEce92De3Edee1F18E0157C05861564", "label": "Uniswap V3 SwapRouter", "category": "dex"},
        {"address": "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45", "label": "Uniswap V3 SwapRouter02", "category": "dex"},
        {"address": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D", "label": "Uniswap V2 Router 02", "category": "dex"},
        {"address": "0x1111111254EEB25477B68fb85Ed929f73A960582", "label": "1inch v5 Aggregation Router", "category": "dex"},
        {"address": "0x111111125421cA6dc452d289314280a0f8842A65", "label": "1inch v6 Aggregation Router", "category": "dex"},
        {"address": "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2", "label": "Aave V3 Pool", "category": "lending"},
        {"address": "0xc3d688B66703497DAA19211EEdff47f25384cdc3", "label": "Compound V3 USDC", "category": "lending"},
        {"address": "0x00000000219ab540356cBB839Cbe05303d7705Fa", "label": "Beacon Deposit Contract (ETH staking)", "category": "staking"},
        {"address": "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84", "label": "Lido stETH", "category": "staking"},
    ],
    8453: [
        {"address": "0x2626664c2603336E57B271c5C0b26F421741e481", "label": "Uniswap V3 SwapRouter02 (Base)", "category": "dex"},
        {"address": "0x6fF5693b99212Da76ad316178A184AB56D299b43", "label": "Uniswap Universal Router (Base)", "category": "dex"},
        {"address": "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43", "label": "Aerodrome Router", "category": "dex"},
        {"address": "0xA238Dd80C259a72e81d7e4664a9801593F98d1c5", "label": "Aave V3 Pool (Base)", "category": "lending"},
        {"address": "0xb125E6687d4313864e53df431d5425969c15Eb2F", "label": "Compound V3 USDC (Base)", "category": "lending"},
    ],
}


@app.get("/api/safe-contracts")
async def list_safe_contracts(chain_id: int) -> list:
    if chain_id not in CHAINS:
        raise HTTPException(status_code=400, detail=f"unsupported chain {chain_id}")
    return SAFE_CONTRACTS.get(chain_id, [])


# --- Contacts (user-defined address book) ---
# Stored as JSON on the Seagate, mirrored to SD backup like the keystore.
CONTACTS_FILENAME = "contacts.json"


def contacts_paths() -> Dict[str, Path]:
    return {
        "primary": DATA_PATH / CONTACTS_FILENAME,
        "backup":  BACKUP_PATH / CONTACTS_FILENAME,
    }


def load_contacts() -> list:
    p = contacts_paths()["primary"]
    if not p.exists():
        b = contacts_paths()["backup"]
        if b.exists():
            try:
                return json.loads(b.read_text())
            except Exception:
                logger.exception("contacts backup unreadable")
        return []
    try:
        return json.loads(p.read_text())
    except Exception:
        logger.exception("contacts primary unreadable")
        return []


def save_contacts(contacts: list) -> None:
    """Atomic write to primary; mirror to backup. Same pattern as keystore."""
    payload = json.dumps(contacts, indent=2)
    for label, path in contacts_paths().items():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(path.suffix + ".tmp")
            tmp.write_text(payload)
            tmp.replace(path)
        except Exception:
            logger.exception("failed to write %s contacts at %s", label, path)
            if label == "primary":
                raise


class ContactUpsertRequest(BaseModel):
    address: str
    label: str = Field(min_length=1, max_length=80)
    notes: Optional[str] = Field(default="", max_length=400)
    chain_ids: Optional[list] = None  # None = all chains


@app.get("/api/contacts")
async def get_contacts() -> list:
    """All contacts, all chains. Frontend filters by chain when relevant."""
    return load_contacts()


@app.post("/api/contacts")
async def upsert_contact(body: ContactUpsertRequest) -> Dict[str, Any]:
    """Add a new contact, or update an existing one keyed by lowercased address."""
    _validate_address(body.address, "contact")
    key = body.address.lower()
    contacts = load_contacts()
    now = dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    updated = False
    for c in contacts:
        if c.get("address", "").lower() == key:
            c["address"]  = body.address  # preserve user's casing
            c["label"]    = body.label.strip()
            c["notes"]    = (body.notes or "").strip()
            c["chain_ids"] = body.chain_ids
            c["updated_at"] = now
            updated = True
            break
    if not updated:
        contacts.append({
            "address":   body.address,
            "label":     body.label.strip(),
            "notes":     (body.notes or "").strip(),
            "chain_ids": body.chain_ids,
            "created_at": now,
            "updated_at": now,
        })
    save_contacts(contacts)
    audit("contact.upsert", address=body.address, label=body.label, action="update" if updated else "create")
    return {"ok": True, "updated": updated}


@app.delete("/api/contacts/{address}")
async def delete_contact(address: str) -> Dict[str, Any]:
    _validate_address(address, "contact")
    key = address.lower()
    contacts = load_contacts()
    before = len(contacts)
    contacts = [c for c in contacts if c.get("address", "").lower() != key]
    if len(contacts) == before:
        raise HTTPException(status_code=404, detail="contact not found")
    save_contacts(contacts)
    audit("contact.delete", address=address)
    return {"ok": True}


# ----- Phase 3.0: transaction simulation gate -----
# Decoder for the function selectors most relevant to safety. The point is to
# show the user, in plain language, what a transaction will do BEFORE they
# sign - especially approvals, which are how most drains happen.
MAX_UINT256 = 2**256 - 1

KNOWN_SELECTORS: Dict[str, Dict[str, Any]] = {
    "0xa9059cbb": {"sig": "transfer(address,uint256)",
                   "args": [("to", "address"), ("amount", "uint256")]},
    "0x095ea7b3": {"sig": "approve(address,uint256)",
                   "args": [("spender", "address"), ("amount", "uint256")]},
    "0x23b872dd": {"sig": "transferFrom(address,address,uint256)",
                   "args": [("from", "address"), ("to", "address"), ("amount", "uint256")]},
    "0xa22cb465": {"sig": "setApprovalForAll(address,bool)",
                   "args": [("operator", "address"), ("approved", "bool")]},
    "0x39509351": {"sig": "increaseAllowance(address,uint256)",
                   "args": [("spender", "address"), ("addedValue", "uint256")]},
    "0x42842e0e": {"sig": "safeTransferFrom(address,address,uint256)",
                   "args": [("from", "address"), ("to", "address"), ("tokenId", "uint256")]},
}


def decode_calldata(data: str) -> Dict[str, Any]:
    """Decode known function calls. Returns selector, function sig, args, and
    safety warnings. For unknown selectors, returns the selector with an
    'UNKNOWN_FUNCTION' marker so the UI can lean on simulation instead."""
    d = (data or "").replace("0x", "")
    if len(d) < 8:
        return {"selector": None, "function": "(plain transfer, no calldata)",
                "args": {}, "warnings": []}
    selector = "0x" + d[:8].lower()
    known = KNOWN_SELECTORS.get(selector)
    if not known:
        return {"selector": selector, "function": "unknown",
                "args": {}, "warnings": ["UNKNOWN_FUNCTION"]}

    args_blob = d[8:]
    decoded: Dict[str, Any] = {}
    warnings: list = []
    for i, (name, atype) in enumerate(known["args"]):
        chunk = args_blob[i * 64:(i + 1) * 64]
        if len(chunk) < 64:
            break
        if atype == "address":
            decoded[name] = "0x" + chunk[-40:]
        elif atype == "uint256":
            val = int(chunk, 16)
            if val >= MAX_UINT256 - 10**60:
                decoded[name] = "UNLIMITED"
                if known["sig"].startswith(("approve", "increaseAllowance")):
                    warnings.append("UNLIMITED_APPROVAL")
            else:
                decoded[name] = str(val)
        elif atype == "bool":
            val = int(chunk, 16) != 0
            decoded[name] = val
            if known["sig"].startswith("setApprovalForAll") and val:
                warnings.append("APPROVE_ALL_NFTS")

    return {"selector": selector, "function": known["sig"],
            "args": decoded, "warnings": warnings}


async def eth_call_preflight(chain_id: int, from_addr: str, to: str,
                             value_wei: int, data: str) -> Dict[str, Any]:
    """Run the tx as eth_call to detect reverts before signing. Distinguishes
    a contract revert (will_revert=True + reason) from RPC transport failure
    (raises 502)."""
    chain = CHAINS[chain_id]
    if http_client is None:
        raise HTTPException(status_code=503, detail="http client not initialized")
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "eth_call",
        "params": [{"from": from_addr, "to": to,
                    "value": hex(value_wei), "data": data or "0x"}, "latest"],
    }
    last_err = None
    for url in chain["rpc_urls"]:
        try:
            r = await http_client.post(url, json=payload, timeout=8.0)
            r.raise_for_status()
            j = r.json()
            if "error" in j and j["error"] is not None:
                err = j["error"]
                reason = err.get("message", "execution reverted") if isinstance(err, dict) else str(err)
                return {"will_revert": True, "revert_reason": reason}
            return {"will_revert": False, "revert_reason": None}
        except httpx.HTTPError as e:
            last_err = str(e)
            continue
    raise HTTPException(status_code=502, detail=f"preflight transport failure: {last_err}")


ALCHEMY_NETWORKS = {1: "eth-mainnet", 8453: "base-mainnet"}


async def alchemy_simulate_asset_changes(chain_id: int, key: str, from_addr: str,
                                         to: str, value_wei: int, data: str) -> Optional[Dict[str, Any]]:
    """Use Alchemy's simulateAssetChanges to get a clean list of which assets
    move in/out. Only runs if WALLET_ALCHEMY_KEY is configured."""
    network = ALCHEMY_NETWORKS.get(chain_id)
    if not network or http_client is None:
        return None
    url = f"https://{network}.g.alchemy.com/v2/{key}"
    payload = {
        "jsonrpc": "2.0", "id": 1, "method": "alchemy_simulateAssetChanges",
        "params": [{"from": from_addr, "to": to,
                    "value": hex(value_wei), "data": data or "0x"}],
    }
    r = await http_client.post(url, json=payload, timeout=12.0)
    r.raise_for_status()
    j = r.json()
    if "error" in j and j["error"] is not None:
        raise RuntimeError(f"alchemy error: {j['error']}")
    result = j.get("result", {})
    changes = []
    for c in result.get("changes", []):
        changes.append({
            "asset_type": c.get("assetType"),
            "change_type": c.get("changeType"),
            "from": c.get("from"),
            "to": c.get("to"),
            "amount": c.get("amount"),
            "symbol": c.get("symbol"),
            "name": c.get("name"),
            "decimals": c.get("decimals"),
            "contract": c.get("contractAddress"),
        })
    return {"changes": changes, "sim_error": result.get("error")}


@app.post("/api/tx/simulate")
async def simulate_tx(body: TxEstimateRequest) -> Dict[str, Any]:
    """Simulate a tx before signing: decode the call, detect reverts, and (if
    an Alchemy key is configured) show exactly which assets move."""
    if body.chain_id not in CHAINS:
        raise HTTPException(status_code=400, detail=f"unsupported chain {body.chain_id}")
    _validate_address(body.from_address, "from")
    _validate_address(body.to, "to")
    try:
        value_wei = int(body.value_wei)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid value_wei")

    decoded = decode_calldata(body.data or "0x")

    asset_changes = None
    sim_source = "eth_call"
    alchemy_key = (os.getenv("WALLET_ALCHEMY_KEY") or "").strip()
    if alchemy_key:
        try:
            asset_changes = await alchemy_simulate_asset_changes(
                body.chain_id, alchemy_key, body.from_address, body.to, value_wei, body.data or "0x")
            sim_source = "alchemy"
        except Exception:
            logger.warning("alchemy simulation failed; falling back to eth_call", exc_info=True)

    # Always run the eth_call preflight for revert detection.
    try:
        preflight = await eth_call_preflight(
            body.chain_id, body.from_address, body.to, value_wei, body.data or "0x")
    except HTTPException:
        # Transport failure: we can't confirm safety. Surface as unknown.
        preflight = {"will_revert": None, "revert_reason": "could not reach RPC for preflight"}

    return {
        "chain_id": body.chain_id,
        "decoded": decoded,
        "will_revert": preflight["will_revert"],
        "revert_reason": preflight["revert_reason"],
        "asset_changes": asset_changes,
        "simulation_source": sim_source,
        "alchemy_enabled": bool(alchemy_key),
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
