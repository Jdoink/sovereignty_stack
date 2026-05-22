"""
Sovereignty Stack Wallet Service - Phase 1.

This service generates and securely stores a single Ethereum keypair on the
Pi. The private key never leaves this process; the keystore on disk is
encrypted with an Argon2id-derived AES-256-GCM key.

Phase 1 (this file) intentionally covers ONLY:
  - account creation (returns BIP-39 mnemonic exactly once)
  - keystore existence / address listing
  - serving the latest console.html so the UI is same-origin with the API

Signing, allowlist, simulation, multisig, and YubiKey unlock are deferred to
later phases. See the project README for the phase plan.

All crypto comes from well-known libraries:
  - argon2-cffi (RFC 9106 Argon2id)
  - cryptography (AES-256-GCM)
  - eth-account (BIP-39 / BIP-32 / BIP-44, the same library used by Brownie,
    Ape, web3.py)
No custom crypto. No hashlib for security purposes.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import secrets
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
# FastAPI app
# ============================================================================
http_client: Optional[httpx.AsyncClient] = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global http_client
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(8.0))
    DATA_PATH.mkdir(parents=True, exist_ok=True)
    BACKUP_PATH.mkdir(parents=True, exist_ok=True)
    logger.info("wallet-service ready; data=%s backup=%s", DATA_PATH, BACKUP_PATH)
    try:
        yield
    finally:
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
