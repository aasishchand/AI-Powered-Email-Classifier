"""Encrypt/decrypt mailbox passwords (Fernet)."""
import base64
import os

try:
    from cryptography.fernet import Fernet, InvalidToken
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    InvalidToken = Exception  # type: ignore

# Dev fallback: fixed valid Fernet key so encrypt/decrypt work across restarts. Use MAILBOX_ENCRYPTION_KEY in production.
_DEV_KEY = b"0skgHRQApLkrvUYG4mFj9FUsPhj-0dtGMv7GyOyrsog="


def _fernet():
    raw = os.environ.get("MAILBOX_ENCRYPTION_KEY")
    if raw and len(raw) >= 32 and CRYPTO_AVAILABLE:
        k = raw.encode() if isinstance(raw, str) else raw
        return Fernet(base64.urlsafe_b64encode(k[:32].ljust(32, b"0")[:32]))
    if CRYPTO_AVAILABLE and _DEV_KEY:
        return Fernet(_DEV_KEY)
    raise RuntimeError("Encryption not available: install cryptography and set MAILBOX_ENCRYPTION_KEY or use default.")


def encrypt_password(plain: str) -> str:
    if not CRYPTO_AVAILABLE:
        return plain
    try:
        payload = plain.encode("utf-8", errors="replace")
        return _fernet().encrypt(payload).decode()
    except Exception as e:
        raise ValueError(f"Encryption failed: {e}") from e


def decrypt_password(encrypted: str) -> str:
    if not CRYPTO_AVAILABLE:
        return encrypted
    try:
        return _fernet().decrypt(encrypted.encode()).decode()
    except InvalidToken:
        return ""
