"""
ProofCoin Block Structure and Merkle Tree Engine.

Consensus Rules:
- Header contains version, prev_hash, merkle_root, timestamp, difficulty, nonce, miner_pubkey, solution
- Merkle Root computed via double SHA-256 binary tree over transaction txids
- Timestamp Rules:
    1. Must be strictly greater than Median Time Past (MTP) of last 11 blocks
    2. Must not be more than 7,200 seconds (2 hours) into the future
"""

import json
import time
import hashlib
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from proofcoin.consensus.cunningham import CunninghamChain, verify_cunningham_chain
from proofcoin.core.transaction import Transaction

MAX_FUTURE_BLOCK_TIME_SECONDS: int = 7200  # 2 hours
MTP_WINDOW_SIZE: int = 11


def calculate_merkle_root(tx_hashes: List[str]) -> str:
    """
    Calculate double-SHA256 binary Merkle root from ordered list of txids.
    If tree level has an odd number of elements, the last element is duplicated.
    """
    if not tx_hashes:
        return "00" * 32

    current_level = [bytes.fromhex(h) for h in tx_hashes]

    while len(current_level) > 1:
        if len(current_level) % 2 != 0:
            current_level.append(current_level[-1])

        next_level = []
        for i in range(0, len(current_level), 2):
            combined = current_level[i] + current_level[i + 1]
            parent = hashlib.sha256(hashlib.sha256(combined).digest()).digest()
            next_level.append(parent)
        current_level = next_level

    return current_level[0].hex()


@dataclass
class BlockHeader:
    """Header data structure for PoUW mining and block verification."""
    version: int
    prev_hash: str
    merkle_root: str
    timestamp: int
    difficulty: float
    nonce: int
    miner_pubkey: str
    solution: CunninghamChain

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "prev_hash": self.prev_hash,
            "merkle_root": self.merkle_root,
            "timestamp": self.timestamp,
            "difficulty": self.difficulty,
            "nonce": self.nonce,
            "miner_pubkey": self.miner_pubkey,
            "solution": self.solution.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BlockHeader":
        return cls(
            version=int(data["version"]),
            prev_hash=str(data["prev_hash"]),
            merkle_root=str(data["merkle_root"]),
            timestamp=int(data["timestamp"]),
            difficulty=float(data["difficulty"]),
            nonce=int(data["nonce"]),
            miner_pubkey=str(data["miner_pubkey"]),
            solution=CunninghamChain.from_dict(data["solution"]),
        )

    def calculate_hash(self) -> str:
        """
        Compute deterministic double SHA-256 block header hash.
        """
        canonical_header = {
            "version": self.version,
            "prev_hash": self.prev_hash,
            "merkle_root": self.merkle_root,
            "timestamp": self.timestamp,
            "difficulty": self.difficulty,
            "nonce": self.nonce,
            "miner_pubkey": self.miner_pubkey,
            "solution": self.solution.to_dict(),
        }
        raw = json.dumps(canonical_header, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(hashlib.sha256(raw).digest()).hexdigest()


@dataclass
class Block:
    """Full block containing header and transaction ledger."""
    header: BlockHeader
    transactions: List[Transaction]
    _hash: Optional[str] = field(default=None, init=False, repr=False)

    @property
    def block_hash(self) -> str:
        if self._hash is None:
            self._hash = self.header.calculate_hash()
        return self._hash

    def to_dict(self) -> dict:
        return {
            "hash": self.block_hash,
            "header": self.header.to_dict(),
            "transactions": [tx.to_dict() for tx in self.transactions],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Block":
        header = BlockHeader.from_dict(data["header"])
        transactions = [Transaction.from_dict(tx_data) for tx_data in data["transactions"]]
        return cls(header=header, transactions=transactions)


def calculate_median_time_past(recent_timestamps: List[int]) -> int:
    """
    Computes Median Time Past (MTP) over up to 11 previous block timestamps.
    """
    if not recent_timestamps:
        return 0
    window = sorted(recent_timestamps[-MTP_WINDOW_SIZE:])
    mid = len(window) // 2
    return window[mid]


def validate_block_header(
    header: BlockHeader,
    prev_block_header: Optional[BlockHeader],
    recent_timestamps: List[int],
    current_time: Optional[int] = None,
) -> Tuple[bool, str]:
    """
    Validates BlockHeader against consensus rules:
    - Version validity
    - Previous hash linkage
    - Timestamp > MTP
    - Timestamp <= Current time + 2 hours
    - Cunningham chain PoUW proof against required difficulty
    """
    if header.version < 1:
        return False, "Invalid block version"

    if current_time is None:
        current_time = int(time.time())

    # Check future timestamp drift
    if header.timestamp > current_time + MAX_FUTURE_BLOCK_TIME_SECONDS:
        return False, (
            f"Block timestamp ({header.timestamp}) is too far in future "
            f"(max allowed: {current_time + MAX_FUTURE_BLOCK_TIME_SECONDS})"
        )

    # Check Median Time Past rule
    mtp = calculate_median_time_past(recent_timestamps)
    if header.timestamp <= mtp and prev_block_header is not None:
        return False, f"Block timestamp ({header.timestamp}) <= Median Time Past ({mtp})"

    # Verify PoUW Cunningham Chain Solution
    valid_pouw, reason = verify_cunningham_chain(
        prev_hash=header.prev_hash,
        miner_pubkey=header.miner_pubkey,
        merkle_root=header.merkle_root,
        nonce=header.nonce,
        chain=header.solution,
        required_difficulty=header.difficulty,
    )
    if not valid_pouw:
        return False, f"Invalid Proof of Useful Work: {reason}"

    return True, "Block header is valid"
