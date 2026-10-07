"""
ProofCoin Wallet Architecture.

Capabilities:
- Ed25519 asymmetric key generation
- Checksummed Base58Check address derivation
- Authenticated scrypt + AES-GCM file encryption & backup
- Coin selection algorithm & UTXO spending
- Out-of-band transaction creation, signing, and verification
"""

import os
import json
from typing import Dict, List, Tuple, Optional
from proofcoin.crypto.keys import KeyPair, generate_keypair, sign_data
from proofcoin.crypto.address import pubkey_to_address
from proofcoin.crypto.cipher import encrypt_wallet_payload, decrypt_wallet_payload
from proofcoin.core.transaction import (
    Transaction,
    TxInput,
    TxOutput,
    COIN,
    MAX_MONEY,
)


class Wallet:
    def __init__(self, keypair: Optional[KeyPair] = None):
        self.keypair = keypair or generate_keypair()
        self.address = pubkey_to_address(self.keypair.public_key_hex)

    @classmethod
    def create(cls) -> "Wallet":
        """Generate a pristine new wallet with freshly generated entropy."""
        return cls()

    @classmethod
    def load_from_encrypted_file(cls, filepath: str, passphrase: str) -> "Wallet":
        """Decrypt and deserialize wallet from file."""
        with open(filepath, "r", encoding="utf-8") as f:
            encrypted_data = json.load(f)

        decrypted_bytes = decrypt_wallet_payload(encrypted_data, passphrase)
        wallet_json = json.loads(decrypted_bytes.decode("utf-8"))

        kp = KeyPair(
            private_key_hex=wallet_json["private_key_hex"],
            public_key_hex=wallet_json["public_key_hex"],
        )
        return cls(keypair=kp)

    def save_to_encrypted_file(self, filepath: str, passphrase: str) -> None:
        """Serialize and encrypt wallet keys with scrypt + AES-256-GCM."""
        payload = {
            "address": self.address,
            "public_key_hex": self.keypair.public_key_hex,
            "private_key_hex": self.keypair.private_key_hex,
        }
        raw_bytes = json.dumps(payload).encode("utf-8")
        encrypted_package = encrypt_wallet_payload(raw_bytes, passphrase)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(encrypted_package, f, indent=2)

    def create_transaction(
        self,
        recipient_address: str,
        amount: int,
        fee: int,
        available_utxos: List[Tuple[str, int, int]],  # [(txid, vout, amount)]
    ) -> Transaction:
        """
        Build and sign a UTXO transaction sending coins to recipient_address.
        
        Coin Selection Strategy:
        - Greedy accumulation of smallest UTXOs that cover (amount + fee)
        - Excess amount is returned to wallet's own address as a change output.
        """
        if amount <= 0:
            raise ValueError("Transfer amount must be strictly positive")
        if fee < 0:
            raise ValueError("Fee cannot be negative")
        if amount + fee > MAX_MONEY:
            raise ValueError("Amount + fee exceeds total monetary supply")

        target_total = amount + fee
        selected_utxos = []
        collected_sum = 0

        # Sort UTXOs by amount descending for efficient packing
        for txid, vout, utxo_amount in sorted(available_utxos, key=lambda x: x[2], reverse=True):
            selected_utxos.append((txid, vout, utxo_amount))
            collected_sum += utxo_amount
            if collected_sum >= target_total:
                break

        if collected_sum < target_total:
            raise ValueError(
                f"Insufficient funds: available {collected_sum} units ({collected_sum / COIN:.4f} coins), "
                f"needed {target_total} units ({target_total / COIN:.4f} coins)"
            )

        # Build Inputs (unsigned initially)
        inputs = [
            TxInput(prev_txid=txid, vout=vout, signature="", pubkey=self.keypair.public_key_hex)
            for txid, vout, _ in selected_utxos
        ]

        # Build Outputs
        outputs = [TxOutput(amount=amount, address=recipient_address)]
        change_amount = collected_sum - target_total
        if change_amount > 0:
            outputs.append(TxOutput(amount=change_amount, address=self.address))

        # Build Transaction
        tx = Transaction(version=1, inputs=inputs, outputs=outputs, locktime=0)

        # Sign all inputs
        tx_digest = tx.get_signing_digest()
        for tx_in in tx.inputs:
            tx_in.signature = sign_data(self.keypair.private_key_hex, tx_digest)

        return tx
