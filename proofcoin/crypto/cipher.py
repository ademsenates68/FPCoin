"""
ProofCoin Wallet Encryption Module.

Cryptographic Specification:
- Key Derivation: scrypt (N=16384, r=8, p=1, dklen=32)
- Symmetric Cipher: AES-256-GCM (Authenticated Encryption with Associated Data)
- Salt: 16 cryptographically random bytes (os.urandom)
- Nonce/IV: 12 cryptographically random bytes
- AEAD Tag: 16 bytes verified automatically by AESGCM
"""

import os
import json
import hashlib
from typing import Dict, Any
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


SCRYPT_N = 16384
SCRYPT_R = 8
SCRYPT_P = 1
KEY_LEN = 32


def derive_aes_key(passphrase: str, salt: bytes) -> bytes:
    """
    Derive a 256-bit symmetric encryption key using scrypt KDF.
    """
    if not passphrase:
        raise ValueError("Passphrase cannot be empty")
    return hashlib.scrypt(
        passphrase.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=KEY_LEN,
    )


def encrypt_wallet_payload(data: bytes, passphrase: str) -> Dict[str, Any]:
    """
    Encrypt plaintext bytes using scrypt key derivation and AES-256-GCM.
    Returns:
        JSON-serializable dictionary containing cipher parameters and ciphertext.
    """
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = derive_aes_key(passphrase, salt)

    aesgcm = AESGCM(key)
    # AESGCM.encrypt appends the 16-byte authentication tag to the end of ciphertext
    ciphertext_with_tag = aesgcm.encrypt(nonce, data, None)

    return {
        "kdf": "scrypt",
        "kdf_params": {
            "n": SCRYPT_N,
            "r": SCRYPT_R,
            "p": SCRYPT_P,
            "salt_hex": salt.hex(),
        },
        "cipher": "aes-256-gcm",
        "nonce_hex": nonce.hex(),
        "ciphertext_hex": ciphertext_with_tag.hex(),
    }


def decrypt_wallet_payload(payload: Dict[str, Any], passphrase: str) -> bytes:
    """
    Decrypt an AES-256-GCM encrypted payload using the provided passphrase.
    Raises:
        ValueError if the authentication tag fails (wrong passphrase or tampered data).
    """
    try:
        salt = bytes.fromhex(payload["kdf_params"]["salt_hex"])
        nonce = bytes.fromhex(payload["nonce_hex"])
        ciphertext_with_tag = bytes.fromhex(payload["ciphertext_hex"])
    except (KeyError, TypeError, ValueError) as e:
        raise ValueError(f"Malformed encrypted wallet package: {e}")

    key = derive_aes_key(passphrase, salt)
    aesgcm = AESGCM(key)

    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        return plaintext
    except Exception as e:
        raise ValueError("Decryption failed: invalid passphrase or corrupted wallet file")
