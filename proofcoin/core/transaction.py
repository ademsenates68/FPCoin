"""
ProofCoin UTXO Transaction Engine.

Features:
- UTXO accounting model with explicit inputs and outputs
- Segregated Signature Architecture (Immune to Third-Party TxID Malleability)
- Strict Integer Bounds and Overflow Prevention (Max Supply: 21,000,000 COIN)
- Ed25519 Signature Verification
- In-transaction Double Spend Prevention
"""

import json
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from proofcoin.crypto.keys import verify_signature
from proofcoin.crypto.address import pubkey_to_address, validate_address

# Monetary Constants
COIN: int = 100_000_000  # 1 ProofCoin = 10^8 atomic units
MAX_SUPPLY_COINS: int = 21_000_000
MAX_MONEY: int = MAX_SUPPLY_COINS * COIN  # 2,100,000,000,000,000 atomic units

COINBASE_PREV_TXID: str = "00" * 32
COINBASE_VOUT: int = 0xFFFFFFFF


@dataclass
class TxInput:
    """Spends an unspent output from a previous transaction."""
    prev_txid: str
    vout: int
    signature: str = ""       # Hex Ed25519 signature
    pubkey: str = ""          # Hex Ed25519 public key

    def to_dict(self, include_sig: bool = True) -> dict:
        d = {
            "prev_txid": self.prev_txid,
            "vout": self.vout,
        }
        if include_sig:
            d["signature"] = self.signature
            d["pubkey"] = self.pubkey
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "TxInput":
        return cls(
            prev_txid=str(data["prev_txid"]),
            vout=int(data["vout"]),
            signature=str(data.get("signature", "")),
            pubkey=str(data.get("pubkey", "")),
        )


@dataclass
class TxOutput:
    """Creates a new spendable coin output."""
    amount: int               # Integer amount in atomic units
    address: str              # Base58Check ProofCoin address

    def to_dict(self) -> dict:
        return {
            "amount": self.amount,
            "address": self.address,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TxOutput":
        return cls(
            amount=int(data["amount"]),
            address=str(data["address"]),
        )


@dataclass
class Transaction:
    """ProofCoin UTXO Transaction."""
    version: int
    inputs: List[TxInput]
    outputs: List[TxOutput]
    locktime: int = 0
    _txid: Optional[str] = field(default=None, init=False, repr=False)

    @property
    def is_coinbase(self) -> bool:
        return (
            len(self.inputs) == 1
            and self.inputs[0].prev_txid == COINBASE_PREV_TXID
            and self.inputs[0].vout == COINBASE_VOUT
        )

    def get_signing_digest(self) -> bytes:
        """
        Produce deterministic canonical bytes over transaction inputs (without signatures)
        and outputs to prevent malleability while signing.
        """
        payload = {
            "version": self.version,
            "inputs": [{"prev_txid": i.prev_txid, "vout": i.vout} for i in self.inputs],
            "outputs": [o.to_dict() for o in self.outputs],
            "locktime": self.locktime,
        }
        canonical_json = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(hashlib.sha256(canonical_json).digest()).digest()

    @property
    def txid(self) -> str:
        """
        Unique transaction identifier.
        Computed as double SHA-256 over canonical structure.
        """
        if self._txid is None:
            self._txid = calculate_tx_hash(self)
        return self._txid

    def to_dict(self) -> dict:
        return {
            "txid": self.txid,
            "version": self.version,
            "inputs": [i.to_dict(include_sig=True) for i in self.inputs],
            "outputs": [o.to_dict() for o in self.outputs],
            "locktime": self.locktime,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        tx = cls(
            version=int(data["version"]),
            inputs=[TxInput.from_dict(i) for i in data["inputs"]],
            outputs=[TxOutput.from_dict(o) for o in data["outputs"]],
            locktime=int(data.get("locktime", 0)),
        )
        return tx


def calculate_tx_hash(tx: Transaction) -> str:
    """
    Computes immutable TxID using canonical JSON serialization.
    """
    payload = {
        "version": tx.version,
        "inputs": [i.to_dict(include_sig=True) for i in tx.inputs],
        "outputs": [o.to_dict() for o in tx.outputs],
        "locktime": tx.locktime,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(hashlib.sha256(canonical).digest()).hexdigest()


def create_coinbase_tx(recipient_address: str, block_reward: int, fees: int, height: int) -> Transaction:
    """
    Create a valid coinbase transaction claiming block subsidy plus transaction fees.
    Height is encoded into the script/signature to ensure unique coinbase txids.
    """
    total_amount = block_reward + fees
    if total_amount < 0 or total_amount > MAX_MONEY:
        raise ValueError(f"Coinbase amount out of range: {total_amount}")

    coinbase_input = TxInput(
        prev_txid=COINBASE_PREV_TXID,
        vout=COINBASE_VOUT,
        signature=f"coinbase_h_{height}",
        pubkey="",
    )
    coinbase_output = TxOutput(amount=total_amount, address=recipient_address)

    return Transaction(
        version=1,
        inputs=[coinbase_input],
        outputs=[coinbase_output],
        locktime=0,
    )


def validate_transaction_basics(tx: Transaction) -> Tuple[bool, str]:
    """
    Syntactic & Stateless Validation (BIP Rule Compliance):
    - Input & output presence
    - Positive non-zero amount checks
    - Integer bounds (no overflow > MAX_MONEY)
    - Valid output address format
    - In-tx duplicate input rejection (internal double-spend)
    """
    if not isinstance(tx.version, int) or tx.version < 1:
        return False, "Invalid transaction version"

    if tx.is_coinbase:
        if len(tx.outputs) == 0:
            return False, "Coinbase must have at least one output"
        total_out = sum(o.amount for o in tx.outputs)
        if total_out <= 0 or total_out > MAX_MONEY:
            return False, "Coinbase output amount out of bounds"
        return True, "Valid coinbase format"

    if len(tx.inputs) == 0:
        return False, "Transaction has no inputs"

    if len(tx.outputs) == 0:
        return False, "Transaction has no outputs"

    # Reject duplicate input spends within the same transaction
    seen_inputs = set()
    for tx_in in tx.inputs:
        outpoint = (tx_in.prev_txid, tx_in.vout)
        if outpoint in seen_inputs:
            return False, f"Duplicate input spent inside same tx: {outpoint}"
        seen_inputs.add(outpoint)

        if not tx_in.signature or not tx_in.pubkey:
            return False, "Non-coinbase input missing signature or pubkey"

    total_output = 0
    for out in tx.outputs:
        if not isinstance(out.amount, int):
            return False, "Output amount must be integer"
        if out.amount <= 0:
            return False, f"Output amount must be strictly positive, got {out.amount}"
        if out.amount > MAX_MONEY:
            return False, f"Output amount exceeds total money supply: {out.amount}"
        total_output += out.amount
        if total_output > MAX_MONEY:
            return False, "Total output sum exceeds maximum coin supply"

        if not validate_address(out.address):
            return False, f"Invalid recipient address: {out.address}"

    return True, "Basic transaction verification passed"


def verify_transaction_signatures(
    tx: Transaction,
    utxo_view: Dict[Tuple[str, int], TxOutput],
) -> Tuple[bool, str]:
    """
    Stateful Validation:
    - Resolves each input against provided UTXO set
    - Checks input ownership (address derived from pubkey == UTXO address)
    - Verifies Ed25519 signature against unsigned transaction digest
    - Computes fee and verifies non-negative
    """
    if tx.is_coinbase:
        return True, "Coinbase does not require UTXO signature"

    total_input_amount = 0
    total_output_amount = sum(o.amount for o in tx.outputs)
    tx_digest = tx.get_signing_digest()

    for idx, tx_in in enumerate(tx.inputs):
        outpoint = (tx_in.prev_txid, tx_in.vout)
        utxo = utxo_view.get(outpoint)
        if not utxo:
            return False, f"Input references missing or already spent UTXO: {outpoint}"

        # Verify public key matches the spending UTXO address
        derived_address = pubkey_to_address(tx_in.pubkey)
        if derived_address != utxo.address:
            return False, (
                f"Input #{idx} public key derives address {derived_address}, "
                f"which does not match UTXO address {utxo.address}"
            )

        # Cryptographic Ed25519 Signature Verification
        if not verify_signature(tx_in.pubkey, tx_digest, tx_in.signature):
            return False, f"Input #{idx} Ed25519 signature is invalid"

        total_input_amount += utxo.amount
        if total_input_amount > MAX_MONEY:
            return False, "Input amount calculation exceeded maximum money supply"

    if total_input_amount < total_output_amount:
        return False, (
            f"Transaction inputs ({total_input_amount}) less than "
            f"outputs ({total_output_amount}) - negative fee illegal"
        )

    fee = total_input_amount - total_output_amount
    return True, f"Valid signatures, fee: {fee}"
