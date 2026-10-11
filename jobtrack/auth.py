"""Password hashing and opaque session identifiers."""
import hashlib
import hmac
import secrets
from threading import BoundedSemaphore

_HASH_SLOTS = BoundedSemaphore(2)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    with _HASH_SLOTS:
        digest = hashlib.scrypt(password.encode(), salt=salt, n=2**17, r=8, p=1,
                                maxmem=256 * 1024 * 1024)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    _, salt, expected = encoded.split("$")
    with _HASH_SLOTS:
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=2**17,
                                r=8, p=1, maxmem=256 * 1024 * 1024)
    return hmac.compare_digest(digest.hex(), expected)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# Unknown usernames still go through one password verification.
DUMMY_PASSWORD_HASH = hash_password("invalid-credentials")
