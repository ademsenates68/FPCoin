"""
Unit Tests for ProofCoin Cryptographic Primitives.
"""

import pytest
from proofcoin.crypto.keys import generate_keypair, sign_data, verify_signature, constant_time_compare
from proofcoin.crypto.address import pubkey_to_address, validate_address, b58encode, b58decode
from proofcoin.crypto.cipher import encrypt_wallet_payload, decrypt_wallet_payload


def test_ed25519_keypair_generation():
    kp = generate_keypair()
    assert len(kp.private_key_hex) == 64  # 32 bytes in hex
    assert len(kp.public_key_hex) == 64   # 32 bytes in hex
    assert kp.get_public_bytes() == bytes.fromhex(kp.public_key_hex)
    assert kp.get_private_bytes() == bytes.fromhex(kp.private_key_hex)


def test_ed25519_sign_and_verify():
    kp = generate_keypair()
    message = b"Proof of Useful Work Cunningham Consensus"
    signature = sign_data(kp.private_key_hex, message)

    assert len(signature) == 128  # 64 bytes in hex
    assert verify_signature(kp.public_key_hex, message, signature) is True

    # Tampered message
    assert verify_signature(kp.public_key_hex, b"Tampered Message", signature) is False

    # Tampered signature
    tampered_sig = ("00" if signature[:2] != "00" else "11") + signature[2:]
    assert verify_signature(kp.public_key_hex, message, tampered_sig) is False

    # Wrong public key
    other_kp = generate_keypair()
    assert verify_signature(other_kp.public_key_hex, message, signature) is False


def test_constant_time_comparison():
    val1 = b"cryptographic_constant_time_token_123"
    val2 = b"cryptographic_constant_time_token_123"
    val3 = b"cryptographic_constant_time_token_456"

    assert constant_time_compare(val1, val2) is True
    assert constant_time_compare(val1, val3) is False


def test_address_derivation_and_checksum():
    kp = generate_keypair()
    address = pubkey_to_address(kp.public_key_hex)

    assert isinstance(address, str)
    assert address.startswith("P")  # ProofCoin version prefix
    assert validate_address(address) is True

    # Corrupting the address must fail checksum
    raw = bytearray(b58decode(address))
    raw[-1] ^= 0xFF  # Flip checksum bit
    corrupted_address = b58encode(bytes(raw))
    assert validate_address(corrupted_address) is False

    # Invalid characters or empty strings
    assert validate_address("") is False
    assert validate_address("Invalid00000000000000000000000") is False


def test_wallet_scrypt_aes_gcm_encryption():
    passphrase = "UltraSecureSuperLongMasterPassword2026!"
    secret_payload = b'{"private_key": "aabbcc", "mnemonic": "useful proof coin"}'

    encrypted = encrypt_wallet_payload(secret_payload, passphrase)
    assert encrypted["cipher"] == "aes-256-gcm"
    assert encrypted["kdf"] == "scrypt"
    assert "ciphertext_hex" in encrypted
    assert "nonce_hex" in encrypted

    # Successful decryption
    decrypted = decrypt_wallet_payload(encrypted, passphrase)
    assert decrypted == secret_payload

    # Decryption with wrong passphrase must fail
    with pytest.raises(ValueError, match="Decryption failed"):
        decrypt_wallet_payload(encrypted, "WrongPassword!")

    # Tampered ciphertext must fail AEAD tag check
    tampered = dict(encrypted)
    ct = bytearray(bytes.fromhex(tampered["ciphertext_hex"]))
    ct[0] ^= 0x01
    tampered["ciphertext_hex"] = ct.hex()

    with pytest.raises(ValueError, match="Decryption failed"):
        decrypt_wallet_payload(tampered, passphrase)
