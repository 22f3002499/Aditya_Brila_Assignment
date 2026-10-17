"""Passwords and JWT tokens.

* Passwords are hashed with scrypt (built into Python) and a random salt.
* After login the API gives out a signed JWT that expires after JWT_EXPIRE_MINUTES.
"""

import hashlib
import hmac
import secrets
import time
from typing import Optional

import jwt  # PyJWT

from .config import settings


# ---------------------------------------------------------------- passwords

def hash_password(plain_password: str) -> str:
    """Return 'scrypt$<salt>$<hash>' (hex text) for storing in the database."""
    salt_bytes = secrets.token_bytes(16)
    hash_bytes = hashlib.scrypt(plain_password.encode("utf-8"), salt=salt_bytes, n=2**14, r=8, p=1)
    return f"scrypt${salt_bytes.hex()}${hash_bytes.hex()}"


def password_matches(plain_password: str, stored_hash: str) -> bool:
    """Check a typed password against the stored hash in constant time."""
    try:
        _label, salt_hex, expected_hex = stored_hash.split("$")
        salt_bytes = bytes.fromhex(salt_hex)
        expected_bytes = bytes.fromhex(expected_hex)
    except ValueError:
        return False
    actual_bytes = hashlib.scrypt(plain_password.encode("utf-8"), salt=salt_bytes, n=2**14, r=8, p=1)
    return hmac.compare_digest(actual_bytes, expected_bytes)


# A throw-away hash used when the username does not exist, so that "unknown user"
# and "wrong password" take the same time (prevents guessing valid usernames).
DUMMY_HASH = hash_password("not-a-real-password")


# ---------------------------------------------------------------- tokens

def create_access_token(username: str) -> str:
    """Build a signed token that says who the user is and when it expires."""
    issued_at = int(time.time())
    token_contents = {
        "sub": username,
        "iat": issued_at,
        "exp": issued_at + settings.jwt_expire_minutes * 60,
    }
    return jwt.encode(token_contents, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def read_username_from_token(token: str) -> Optional[str]:
    """Return the username if the token is genuine and not expired, else None."""
    try:
        token_contents = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],  # only accept the algorithm we use
            options={"require": ["exp", "sub"]},
        )
    except jwt.PyJWTError:  # bad signature, expired, malformed, ...
        return None
    return token_contents["sub"]
