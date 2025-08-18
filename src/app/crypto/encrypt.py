from __future__ import annotations

import base64
import hmac
import os
from hashlib import sha256
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app import config


# ---------------------------
# Fernet helpers
# ---------------------------

def generate_fernet_key() -> str:
    """
    Generate a new Fernet key (URL-safe base64-encoded 32-byte key).
    Paste this into .env as FERNET_KEY=...
    """
    return Fernet.generate_key().decode("ascii")


def _get_fernet() -> Fernet:
    key = config.FERNET_KEY or os.getenv("FERNET_KEY")
    if not key:
        raise RuntimeError(
            "FERNET_KEY is not set. Run `python -m cli secret gen-key` and put it in your .env."
        )
    # Normalize (accept raw or bytes-like); Fernet expects base64 urlsafe bytes
    if isinstance(key, str):
        key_bytes = key.encode("ascii")
    else:
        key_bytes = key
    return Fernet(key_bytes)


def encrypt_str(plaintext: str) -> str:
    """
    Encrypt a UTF-8 string with Fernet. Returns URL-safe base64 token (str).
    """
    f = _get_fernet()
    token = f.encrypt(plaintext.encode("utf-8"))
    return token.decode("ascii")


def decrypt_str(token: str) -> str:
    """
    Decrypt a Fernet token (str) back to plaintext UTF-8.
    Raises ValueError if the token is invalid.
    """
    f = _get_fernet()
    try:
        pt = f.decrypt(token.encode("ascii"))
        return pt.decode("utf-8")
    except InvalidToken as e:
        raise ValueError("Invalid Fernet token") from e


# ---------------------------
# HMAC helpers (optional)
# ---------------------------

def _get_hmac_key() -> bytes:
    key = config.HMAC_KEY or os.getenv("HMAC_KEY")
    if not key:
        raise RuntimeError(
            "HMAC_KEY is not set. You can generate one with `python -m cli secret gen-key --hmac`."
        )
    # Accept raw text; if it looks base64-like, try decode, else use bytes of string
    try:
        # try base64 urlsafe first (won't always succeed)
        return base64.urlsafe_b64decode(key.encode("ascii"))
    except Exception:
        return key.encode("utf-8")


def hmac_sign(data: str) -> str:
    """
    Return hex-encoded HMAC-SHA256 signature for the given data.
    """
    key = _get_hmac_key()
    mac = hmac.new(key, data.encode("utf-8"), sha256).hexdigest()
    return mac


def hmac_verify(data: str, signature_hex: str) -> bool:
    """
    Constant-time verify of hex-encoded HMAC-SHA256 signature.
    """
    try:
        expected = hmac_sign(data)
        # constant-time compare
        return hmac.compare_digest(expected, signature_hex)
    except Exception:
        return False
