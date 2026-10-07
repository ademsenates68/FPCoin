"""
ProofCoin Ed25519 Cryptographic Keys Module.

Features:
- Ed25519 digital signature scheme (RFC 8032)
- High-speed verification and deterministic signing
- Constant-time signature verification safeguards
- Hex serialization and validation
"""

import hmac
from dataclasses import dataclass
from typing import Optional
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature


@dataclass(frozen=True)
class KeyPair:
    """Immutable Ed25519 keypair wrapper with hex representations."""
    private_key_hex: str
    public_key_hex: str

    def get_public_bytes(self) -> bytes:
        return bytes.fromhex(self.public_key_hex)

    def get_private_bytes(self) -> bytes:
        return bytes.fromhex(self.private_key_hex)


def generate_keypair() -> KeyPair:
    """
    Generate a cryptographically secure Ed25519 keypair using OS entropy.
    Returns:
        KeyPair containing hex-encoded private and public keys.
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    priv_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )

    return KeyPair(
        private_key_hex=priv_bytes.hex(),
        public_key_hex=pub_bytes.hex(),
    )


def sign_data(private_key_hex: str, message: bytes) -> str:
    """
    Sign arbitrary byte payload using Ed25519 private key.

    Security Note:
    - Ed25519 is deterministic (RFC 8032); it does not require an external RNG
      during signing, mitigating catastrophic nonce-reuse vulnerabilities present in ECDSA.
    """
    if not isinstance(message, (bytes, bytearray)):
        raise TypeError("Message must be bytes or bytearray")

    priv_bytes = bytes.fromhex(private_key_hex)
    if len(priv_bytes) != 32:
        raise ValueError("Ed25519 private key must be exactly 32 bytes (64 hex characters)")

    private_key = ed25519.Ed25519PrivateKey.from_private_bytes(priv_bytes)
    signature = private_key.sign(bytes(message))
    return signature.hex()


def verify_signature(public_key_hex: str, message: bytes, signature_hex: str) -> bool:
    """
    Verify Ed25519 signature in constant-time semantics.

    Returns:
        True if the signature is authentic and valid; False otherwise.
    """
    if not isinstance(message, (bytes, bytearray)):
        return False

    try:
        pub_bytes = bytes.fromhex(public_key_hex)
        sig_bytes = bytes.fromhex(signature_hex)
    except (ValueError, TypeError):
        return False

    if len(pub_bytes) != 32 or len(sig_bytes) != 64:
        return False

    try:
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
        public_key.verify(sig_bytes, bytes(message))
        return True
    except InvalidSignature:
        return False
    except Exception:
        return False


def constant_time_compare(val1: bytes, val2: bytes) -> bool:
    """
    Constant-time comparison to prevent side-channel timing attacks.
    """
    return hmac.compare_digest(val1, val2)
