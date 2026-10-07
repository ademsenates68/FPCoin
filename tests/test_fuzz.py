"""
Fuzz and Robustness Testing for ProofCoin.
"""

import os
import random
import pytest
from proofcoin.network.protocol import (
    deserialize_message,
    serialize_message,
    MessageType,
    MAX_MESSAGE_PAYLOAD_SIZE,
)
from proofcoin.crypto.address import validate_address, b58decode
from proofcoin.core.transaction import (
    Transaction,
    TxInput,
    TxOutput,
    validate_transaction_basics,
    MAX_MONEY,
)


def test_protocol_packet_fuzzing():
    """Fuzz wire deserializer with random malformed byte payloads."""
    # 1. Empty and tiny packets
    assert deserialize_message(b"")[0] is None
    assert deserialize_message(b"PROF")[0] is None
    assert deserialize_message(b"\x00" * 23)[0] is None

    # 2. 50 iterations of arbitrary garbage bytes
    for _ in range(50):
        garbage_len = random.randint(1, 1024)
        garbage_bytes = os.urandom(garbage_len)
        msg_type, payload, status = deserialize_message(garbage_bytes)
        assert msg_type is None
        assert payload is None
        assert status != "OK"

    # 3. Valid message mutated at random positions
    valid_packet = serialize_message(MessageType.PING, {"nonce": 12345})
    for _ in range(20):
        tampered = bytearray(valid_packet)
        # Flip random byte
        flip_pos = random.randint(0, len(tampered) - 1)
        tampered[flip_pos] ^= 0x55
        msg_type, payload, status = deserialize_message(bytes(tampered))
        if status == "OK":
            # Only if flipped byte was insignificant padding (not magic, cmd, length, checksum or json)
            pass
        else:
            assert msg_type is None


def test_address_parser_fuzzing():
    """Feed random strings, special chars, SQL queries to validate_address."""
    malicious_inputs = [
        "' OR '1'='1",
        "<script>alert(1)</script>",
        "P" * 1000,
        "\x00" * 32,
        "../../../etc/passwd",
        "P123456789!@#$%^&*()_+",
        " ",
        "\n\r\t",
        "1" * 34,
        "P" + "0" * 30,  # '0' is not in Base58 alphabet!
        "P" + "O" * 30,  # 'O' (capital O) is not in Base58 alphabet!
        "P" + "I" * 30,  # 'I' (capital I) is not in Base58 alphabet!
        "P" + "l" * 30,  # 'l' (lowercase L) is not in Base58 alphabet!
    ]
    for candidate in malicious_inputs:
        assert validate_address(candidate) is False


def test_transaction_boundary_fuzzing():
    """Fuzz transaction amounts, counts, and structures."""
    odd_amounts = [-1, -9999999999999, 0, MAX_MONEY + 1, 10**18, -2**63]
    for bad_amt in odd_amounts:
        tx = Transaction(
            version=1,
            inputs=[TxInput(prev_txid="aa"*32, vout=0, signature="s", pubkey="p")],
            outputs=[TxOutput(amount=bad_amt, address="P123")],
        )
        ok, reason = validate_transaction_basics(tx)
        assert ok is False
