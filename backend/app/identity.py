from __future__ import annotations

import logging
from pathlib import Path

from nacl.encoding import Base64Encoder
from nacl.signing import SigningKey, VerifyKey

from app.config import settings

logger = logging.getLogger(__name__)

_signing_key: SigningKey | None = None
_verify_key: VerifyKey | None = None


def _identity_dir() -> Path:
    return Path(settings.data_dir) / "identity"


def init_identity() -> None:
    global _signing_key, _verify_key

    identity_dir = _identity_dir()
    identity_dir.mkdir(parents=True, exist_ok=True)
    private_path = identity_dir / "private.key"
    public_path = identity_dir / "public.key"

    if private_path.exists():
        raw = private_path.read_bytes()
        _signing_key = SigningKey(raw)
        logger.info("Loaded existing Ed25519 identity")
    else:
        _signing_key = SigningKey.generate()
        private_path.write_bytes(bytes(_signing_key))
        private_path.chmod(0o600)
        logger.info("Generated new Ed25519 identity")

    _verify_key = _signing_key.verify_key
    public_path.write_text(get_public_key_b64())


def get_signing_key() -> SigningKey:
    if _signing_key is None:
        raise RuntimeError("Identity not initialized — call init_identity() first")
    return _signing_key


def get_verify_key() -> VerifyKey:
    if _verify_key is None:
        raise RuntimeError("Identity not initialized — call init_identity() first")
    return _verify_key


def get_public_key_b64() -> str:
    return get_verify_key().encode(encoder=Base64Encoder).decode()


def get_agent_card() -> dict:
    """Return an A2A v1.0 compliant Agent Card."""
    base_url = settings.external_url.rstrip("/")

    return {
        "name": settings.agent_name,
        "description": f"Agent-to-agent communication layer — owned by {settings.owner_name}",
        "version": "1.0.0",
        "supportedInterfaces": [
            {
                "url": f"{base_url}/a2a",
                "protocolBinding": "HTTP+JSON",
                "protocolVersion": "1.0",
            },
        ],
        "provider": {
            "organization": settings.owner_name,
            "url": base_url,
        },
        "capabilities": {
            "streaming": False,
            "pushNotifications": True,
        },
        "securitySchemes": {
            "bearerJwt": {
                "httpAuthSecurityScheme": {
                    "scheme": "Bearer",
                    "bearerFormat": "JWT (EdDSA / Ed25519)",
                    "description": "Short-lived JWT signed with the sender's Ed25519 key.",
                },
            },
        },
        "securityRequirements": [{"bearerJwt": []}],
        "defaultInputModes": ["application/json", "text/plain"],
        "defaultOutputModes": ["application/json", "text/plain"],
        "skills": [
            {
                "id": "messaging",
                "name": "Agent Communication",
                "description": "Send and receive structured messages between agents.",
                "tags": ["messaging", "a2a"],
            },
        ],
        "metadata": {
            "publicKey": get_public_key_b64(),
        },
    }
