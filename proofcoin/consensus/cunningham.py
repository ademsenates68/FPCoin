"""
ProofCoin Cunningham Prime Chain Mining Module.

Mathematical Background:
A Cunningham chain of the first kind (1CC) is a sequence of primes (p_0, p_1, ..., p_{k-1})
such that p_{i+1} = 2 * p_i + 1 for each 0 <= i < k - 1.

A Cunningham chain of the second kind (2CC) is a sequence of primes where:
p_{i+1} = 2 * p_i - 1.

In ProofCoin:
1. Useful Work: Cunningham chains contribute to computational number theory and
   large prime research (Euler totient records, Sophie Germain primes, cryptography).
2. Anti-Theft Binding:
   The candidate origin prime p_0 is deterministically derived from:
   Hash(prev_hash || miner_pubkey || merkle_root || nonce).
   If an adversary attempts to replace miner_pubkey with their own to hijack
   the block reward, p_0 changes completely and the prime chain breaks.
3. Fast Verification:
   Checking chain validity requires exactly k Miller-Rabin tests (taking < 1 millisecond).
"""

import hashlib
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Tuple
from .prime import is_prime


class ChainType(str, Enum):
    FIRST_KIND = "1CC"   # p_{i+1} = 2 * p_i + 1
    SECOND_KIND = "2CC"  # p_{i+1} = 2 * p_i - 1


@dataclass
class CunninghamChain:
    """Represents a validated Cunningham prime chain solution."""
    chain_type: ChainType
    origin: int
    length: int
    primes: List[int]

    def to_dict(self) -> dict:
        return {
            "chain_type": self.chain_type.value,
            "origin": str(self.origin),
            "length": self.length,
            "primes": [str(p) for p in self.primes],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CunninghamChain":
        return cls(
            chain_type=ChainType(data["chain_type"]),
            origin=int(data["origin"]),
            length=int(data["length"]),
            primes=[int(p) for p in data["primes"]],
        )


def derive_candidate_origin(
    prev_hash: str,
    miner_pubkey: str,
    merkle_root: str,
    nonce: int,
    modulus: int = 1_000_000_000_000,
) -> int:
    """
    Derive deterministic prime candidate origin bound to header & miner pubkey.
    
    Security:
    Cryptographic diffusion ensures an attacker cannot re-use nonce or chain
    with a different miner public key or previous hash.
    """
    payload = f"{prev_hash}:{miner_pubkey}:{merkle_root}:{nonce}".encode("utf-8")
    digest = hashlib.sha256(hashlib.sha256(payload).digest()).digest()

    raw_val = int.from_bytes(digest[:8], byteorder="big")
    # Ensure odd integer and reasonable bit magnitude for deterministic exploration
    candidate = (raw_val % modulus) * 2 + 1
    if candidate < 3:
        candidate = 3
    return candidate


def evaluate_chain(origin: int, chain_type: ChainType, max_length: int = 10) -> List[int]:
    """
    Evaluate the consecutive primes forming a Cunningham chain from origin.
    Returns list of verified prime elements.
    """
    if not is_prime(origin):
        return []

    primes = [origin]
    current = origin

    for _ in range(1, max_length):
        if chain_type == ChainType.FIRST_KIND:
            next_val = 2 * current + 1
        else:
            next_val = 2 * current - 1

        if not is_prime(next_val):
            break

        primes.append(next_val)
        current = next_val

    return primes


def verify_cunningham_chain(
    prev_hash: str,
    miner_pubkey: str,
    merkle_root: str,
    nonce: int,
    chain: CunninghamChain,
    required_difficulty: float,
) -> Tuple[bool, str]:
    """
    Verify proof of useful work.
    
    1. Checks candidate origin derivation matches header fields & miner_pubkey.
    2. Verifies chain length satisfies required difficulty.
    3. Re-verifies every prime in the sequence using Miller-Rabin.
    """
    expected_origin = derive_candidate_origin(prev_hash, miner_pubkey, merkle_root, nonce)
    if chain.origin != expected_origin:
        return False, f"Origin mismatch: got {chain.origin}, expected {expected_origin}"

    if chain.length < int(required_difficulty):
        return False, f"Insufficient chain length: {chain.length} < difficulty {required_difficulty}"

    if len(chain.primes) != chain.length:
        return False, "Chain prime list count does not match declared length"

    if chain.primes[0] != expected_origin:
        return False, "Initial prime does not match derived origin"

    # Verify chain recurrence and primality
    current = chain.primes[0]
    if not is_prime(current):
        return False, f"Origin {current} is not prime"

    for i in range(1, chain.length):
        expected_next = (
            (2 * current + 1)
            if chain.chain_type == ChainType.FIRST_KIND
            else (2 * current - 1)
        )
        if chain.primes[i] != expected_next:
            return False, f"Invalid chain progression at index {i}"
        if not is_prime(expected_next):
            return False, f"Chain member at index {i} ({expected_next}) is composite"
        current = expected_next

    return True, "Valid Cunningham chain"


def mine_cunningham_chain(
    prev_hash: str,
    miner_pubkey: str,
    merkle_root: str,
    target_difficulty: float,
    start_nonce: int = 0,
    max_iterations: int = 100_000,
) -> Optional[Tuple[int, CunninghamChain]]:
    """
    Mine for a valid Cunningham chain satisfying target difficulty.
    Returns (nonce, CunninghamChain) on success, or None if max_iterations exceeded.
    """
    req_len = int(target_difficulty)

    for step in range(max_iterations):
        nonce = start_nonce + step
        candidate = derive_candidate_origin(prev_hash, miner_pubkey, merkle_root, nonce)

        # Quick small prime check on candidate
        if not is_prime(candidate):
            continue

        # Check First Kind (1CC)
        primes_1cc = evaluate_chain(candidate, ChainType.FIRST_KIND, max_length=req_len + 2)
        if len(primes_1cc) >= req_len:
            return nonce, CunninghamChain(
                chain_type=ChainType.FIRST_KIND,
                origin=candidate,
                length=len(primes_1cc),
                primes=primes_1cc,
            )

        # Check Second Kind (2CC)
        primes_2cc = evaluate_chain(candidate, ChainType.SECOND_KIND, max_length=req_len + 2)
        if len(primes_2cc) >= req_len:
            return nonce, CunninghamChain(
                chain_type=ChainType.SECOND_KIND,
                origin=candidate,
                length=len(primes_2cc),
                primes=primes_2cc,
            )

    return None
