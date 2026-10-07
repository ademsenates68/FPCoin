"""
ProofCoin Address Encoding and Validation Module.

Address Standard:
- Base58Check encoding with 1-byte version prefix (0x37 -> addresses starting with 'P')
- Payload: 20-byte double SHA-256 digest of Ed25519 public key
- Checksum: 4-byte double SHA-256 of (version + payload)
- Total binary length: 25 bytes
"""

import hashlib
import hmac

BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
ADDRESS_VERSION = b"\x37"  # Generates addresses starting with 'P'


def b58encode(data: bytes) -> str:
    """Encode bytes to Base58 string preserving leading zero bytes."""
    n = int.from_bytes(data, byteorder="big")
    chars = []
    while n > 0:
        n, rem = divmod(n, 58)
        chars.append(BASE58_ALPHABET[rem])
    encoded = "".join(reversed(chars))

    # Pad leading zero bytes with '1'
    pad = 0
    for byte in data:
        if byte == 0:
            pad += 1
        else:
            break
    return (BASE58_ALPHABET[0] * pad) + encoded


def b58decode(s: str) -> bytes:
    """Decode Base58 string back to bytes preserving leading zeros."""
    if not isinstance(s, str) or not s:
        raise ValueError("Invalid Base58 string")

    pad = 0
    for c in s:
        if c == BASE58_ALPHABET[0]:
            pad += 1
        else:
            break

    n = 0
    for c in s:
        idx = BASE58_ALPHABET.find(c)
        if idx == -1:
            raise ValueError(f"Invalid character in Base58: '{c}'")
        n = n * 58 + idx

    raw = n.to_bytes((n.bit_length() + 7) // 8, byteorder="big") if n > 0 else b""
    return (b"\x00" * pad) + raw


def pubkey_to_address(public_key_hex: str) -> str:
    """
    Derive ProofCoin Base58Check address from an Ed25519 public key hex string.
    Formula:
      h = SHA256(SHA256(pubkey_bytes))[:20]
      checksum = SHA256(SHA256(version + h))[:4]
      address = Base58(version + h + checksum)
    """
    pub_bytes = bytes.fromhex(public_key_hex)
    if len(pub_bytes) != 32:
        raise ValueError("Ed25519 public key must be 32 bytes")

    # Hash public key: double SHA-256 truncated to 20 bytes
    h1 = hashlib.sha256(pub_bytes).digest()
    key_hash = hashlib.sha256(h1).digest()[:20]

    payload = ADDRESS_VERSION + key_hash
    chk = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
    return b58encode(payload + chk)


def validate_address(address: str) -> bool:
    """
    Validate that an address is well-formed and matches its 4-byte checksum.
    Returns:
        True if valid ProofCoin address, False otherwise.
    """
    if not isinstance(address, str) or len(address) < 25 or len(address) > 40:
        return False

    try:
        raw = b58decode(address)
    except Exception:
        return False

    if len(raw) != 25:
        return False

    if raw[0:1] != ADDRESS_VERSION:
        return False

    payload = raw[:21]
    expected_chk = raw[21:25]
    computed_chk = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]

    return hmac.compare_digest(expected_chk, computed_chk)
