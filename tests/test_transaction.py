"""
Unit Tests for ProofCoin UTXO Transactions and Cryptographic Verification.
"""

import pytest
from proofcoin.crypto.keys import generate_keypair, sign_data
from proofcoin.crypto.address import pubkey_to_address
from proofcoin.core.transaction import (
    COIN,
    MAX_MONEY,
    TxInput,
    TxOutput,
    Transaction,
    create_coinbase_tx,
    validate_transaction_basics,
    verify_transaction_signatures,
)


def test_coinbase_transaction():
    kp = generate_keypair()
    addr = pubkey_to_address(kp.public_key_hex)
    cb = create_coinbase_tx(addr, 50 * COIN, 0, height=1)

    assert cb.is_coinbase is True
    assert len(cb.inputs) == 1
    assert len(cb.outputs) == 1
    assert cb.outputs[0].amount == 50 * COIN
    assert cb.outputs[0].address == addr

    valid, reason = validate_transaction_basics(cb)
    assert valid is True


def test_valid_utxo_transfer():
    # Setup Alice and Bob
    alice_kp = generate_keypair()
    alice_addr = pubkey_to_address(alice_kp.public_key_hex)

    bob_kp = generate_keypair()
    bob_addr = pubkey_to_address(bob_kp.public_key_hex)

    # Alice has a 10 coin UTXO
    prev_txid = "a1" * 32
    vout = 0
    utxo_view = {(prev_txid, vout): TxOutput(amount=10 * COIN, address=alice_addr)}

    # Alice sends 6 coins to Bob, 3.9 coins change to herself, 0.1 coin fee
    tx_in = TxInput(prev_txid=prev_txid, vout=vout, signature="", pubkey=alice_kp.public_key_hex)
    tx_out_bob = TxOutput(amount=6 * COIN, address=bob_addr)
    tx_out_alice_change = TxOutput(amount=390_000_000, address=alice_addr)

    tx = Transaction(
        version=1,
        inputs=[tx_in],
        outputs=[tx_out_bob, tx_out_alice_change],
    )

    # Sign transaction
    digest = tx.get_signing_digest()
    tx.inputs[0].signature = sign_data(alice_kp.private_key_hex, digest)

    # Stateless validation
    ok_basic, msg_basic = validate_transaction_basics(tx)
    assert ok_basic is True

    # Stateful signature and UTXO validation
    ok_sigs, msg_sigs = verify_transaction_signatures(tx, utxo_view)
    assert ok_sigs is True
    assert "fee: 10000000" in msg_sigs  # 0.1 coin fee


def test_double_spend_inside_transaction():
    alice_kp = generate_keypair()
    alice_addr = pubkey_to_address(alice_kp.public_key_hex)

    # Attacker tries to spend the exact same UTXO twice in one transaction
    tx_in1 = TxInput(prev_txid="ff"*32, vout=0, signature="sig1", pubkey=alice_kp.public_key_hex)
    tx_in2 = TxInput(prev_txid="ff"*32, vout=0, signature="sig2", pubkey=alice_kp.public_key_hex)

    tx = Transaction(
        version=1,
        inputs=[tx_in1, tx_in2],
        outputs=[TxOutput(amount=10 * COIN, address=alice_addr)],
    )

    ok, reason = validate_transaction_basics(tx)
    assert ok is False
    assert "Duplicate input" in reason


def test_negative_and_zero_amount_rejection():
    alice_kp = generate_keypair()
    alice_addr = pubkey_to_address(alice_kp.public_key_hex)

    # Zero amount
    tx_zero = Transaction(
        version=1,
        inputs=[TxInput(prev_txid="01"*32, vout=0, signature="sig", pubkey=alice_kp.public_key_hex)],
        outputs=[TxOutput(amount=0, address=alice_addr)],
    )
    ok_zero, _ = validate_transaction_basics(tx_zero)
    assert ok_zero is False

    # Negative amount
    tx_neg = Transaction(
        version=1,
        inputs=[TxInput(prev_txid="01"*32, vout=0, signature="sig", pubkey=alice_kp.public_key_hex)],
        outputs=[TxOutput(amount=-500, address=alice_addr)],
    )
    ok_neg, _ = validate_transaction_basics(tx_neg)
    assert ok_neg is False


def test_monetary_overflow_rejection():
    alice_kp = generate_keypair()
    alice_addr = pubkey_to_address(alice_kp.public_key_hex)

    tx_overflow = Transaction(
        version=1,
        inputs=[TxInput(prev_txid="01"*32, vout=0, signature="sig", pubkey=alice_kp.public_key_hex)],
        outputs=[TxOutput(amount=MAX_MONEY + 1, address=alice_addr)],
    )
    ok, reason = validate_transaction_basics(tx_overflow)
    assert ok is False
    assert "exceeds" in reason.lower()


def test_unauthorized_key_and_signature_failure():
    alice_kp = generate_keypair()
    alice_addr = pubkey_to_address(alice_kp.public_key_hex)

    attacker_kp = generate_keypair()

    prev_txid = "bb" * 32
    vout = 0
    utxo_view = {(prev_txid, vout): TxOutput(amount=5 * COIN, address=alice_addr)}

    # Attacker tries to spend Alice's UTXO with attacker's public key
    tx = Transaction(
        version=1,
        inputs=[TxInput(prev_txid=prev_txid, vout=vout, signature="", pubkey=attacker_kp.public_key_hex)],
        outputs=[TxOutput(amount=4 * COIN, address=pubkey_to_address(attacker_kp.public_key_hex))],
    )
    digest = tx.get_signing_digest()
    tx.inputs[0].signature = sign_data(attacker_kp.private_key_hex, digest)

    # Must be rejected because public key does NOT hash to UTXO address!
    ok, reason = verify_transaction_signatures(tx, utxo_view)
    assert ok is False
    assert "does not match UTXO address" in reason
