"""A2A authentication helpers.

Provides short-lived JWT tokens signed with our Ed25519 private key for
outbound requests, and verification of inbound JWTs against a contact's
known public key.
"""
from __future__ import annotations

import time

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from nacl.encoding import Base64Encoder
from nacl.signing import VerifyKey

from app.config import settings
from app.identity import get_signing_key, get_public_key_b64

JWT_ALGORITHM = "EdDSA"
JWT_LIFETIME_SECONDS = 120


def _nacl_to_crypto_private() -> Ed25519PrivateKey:
    """Convert our PyNaCl SigningKey to a cryptography Ed25519PrivateKey."""
    sk = get_signing_key()
    raw_seed = bytes(sk)  # 32-byte seed
    return Ed25519PrivateKey.from_private_bytes(raw_seed)


def _b64_to_crypto_public(pub_b64: str) -> Ed25519PublicKey:
    """Convert a base64-encoded Ed25519 public key to a cryptography key object."""
    vk = VerifyKey(pub_b64.encode(), encoder=Base64Encoder)
    return Ed25519PublicKey.from_public_bytes(bytes(vk))


def build_a2a_jwt() -> str:
    """Create a short-lived JWT signed with our Ed25519 key."""
    private_key = _nacl_to_crypto_private()

    now = int(time.time())
    payload = {
        "sub": settings.external_url,
        "pub": get_public_key_b64(),
        "iat": now,
        "exp": now + JWT_LIFETIME_SECONDS,
    }
    return jwt.encode(payload, private_key, algorithm=JWT_ALGORITHM)


def verify_a2a_jwt(token: str, expected_public_key_b64: str) -> dict | None:
    """Verify and decode a JWT using the sender's known Ed25519 public key.

    Returns the decoded claims dict on success, None on any failure.
    """
    try:
        public_key = _b64_to_crypto_public(expected_public_key_b64)
        return jwt.decode(token, public_key, algorithms=[JWT_ALGORITHM])
    except Exception:
        return None
