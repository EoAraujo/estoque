"""
Gerenciamento das chaves VAPID para Web Push (Fase 5).

Gera um par de chaves no primeiro uso e armazena no settings.
Em produção, defina VAPID_PRIVATE_KEY e VAPID_PUBLIC_KEY no .env
para persistir entre deploys.
"""
import base64
import os

from cryptography.hazmat.primitives import serialization
from django.conf import settings


def _b64url_decode(data: str) -> bytes:
    """Decodifica base64url com padding."""
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _public_key_to_urlsafe(public_key) -> str:
    """Converte a public key de py_vapid para urlsafe base64 (formato VAPID)."""
    raw = public_key.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def ensure_vapid_keys():
    """Garante que existam chaves VAPID em settings."""
    from py_vapid import Vapid02
    if not getattr(settings, "VAPID_PRIVATE_KEY", None) or \
       not getattr(settings, "VAPID_PUBLIC_KEY", None):
        vapid = Vapid02()
        vapid.generate_keys()
        settings.VAPID_PRIVATE_KEY = vapid.private_pem().decode("ascii")
        settings.VAPID_PUBLIC_KEY = _public_key_to_urlsafe(vapid._public_key)


def get_vapid_public_key() -> str:
    ensure_vapid_keys()
    return settings.VAPID_PUBLIC_KEY


def get_vapid_private_key() -> str:
    ensure_vapid_keys()
    return settings.VAPID_PRIVATE_KEY


def get_vapid_claims():
    """Claims VAPID (subject = mailto:admin@...)."""
    ensure_vapid_keys()
    return {
        "sub": os.environ.get(
            "VAPID_CLAIMS_SUB",
            "mailto:admin@estoque.local",
        ),
    }
