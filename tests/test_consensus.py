"""
Unit Tests for ProofCoin Consensus and Cunningham Chains.
"""

import pytest
from proofcoin.consensus.prime import is_prime, miller_rabin
from proofcoin.consensus.cunningham import (
    CunninghamChain,
    ChainType,
    derive_candidate_origin,
    verify_cunningham_chain,
    mine_cunningham_chain,
    evaluate_chain,
)
from proofcoin.consensus.difficulty import (
    calculate_next_difficulty,
    DIFFICULTY_EPOCH_BLOCKS,
    TARGET_BLOCK_TIME_SECONDS,
    MIN_DIFFICULTY,
)


def test_miller_rabin_primes_and_composites():
    known_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 89, 1009, 1000000007, 2147483647]
    for p in known_primes:
        assert is_prime(p) is True, f"{p} should be identified as prime"

    known_composites = [-5, 0, 1, 4, 6, 8, 9, 15, 21, 25, 27, 49, 100, 1000, 1000000]
    for c in known_composites:
        assert is_prime(c) is False, f"{c} should be identified as composite"

    # Carmichael numbers fool simple Fermat tests, but Miller-Rabin must detect them as composite
    carmichael_numbers = [561, 1105, 1729, 2465, 2821, 6601]
    for carm in carmichael_numbers:
        assert is_prime(carm) is False, f"Carmichael number {carm} must be recognized as composite"


def test_cunningham_chain_evaluation():
    # 2 is prime, 2*2+1 = 5 (prime), 2*5+1 = 11 (prime), 2*11+1 = 23 (prime), 2*23+1 = 47 (prime), 2*47+1 = 95 (composite)
    primes_1cc = evaluate_chain(2, ChainType.FIRST_KIND, max_length=10)
    assert primes_1cc == [2, 5, 11, 23, 47]
    assert len(primes_1cc) == 5

    # Second kind: 1531, 2*1531 - 1 = 3061 (prime), 2*3061 - 1 = 6121 (prime), 2*6121 - 1 = 12241 (prime), 2*12241 - 1 = 24481 (prime)
    primes_2cc = evaluate_chain(1531, ChainType.SECOND_KIND, max_length=10)
    assert primes_2cc == [1531, 3061, 6121, 12241, 24481]
    assert len(primes_2cc) == 5


def test_anti_theft_solution_binding():
    prev_hash = "ab" * 32
    merkle_root = "cd" * 32
    legitimate_miner_pubkey = "11" * 32
    attacker_miner_pubkey = "22" * 32

    # Mine a valid chain for legitimate miner
    mine_res = mine_cunningham_chain(
        prev_hash=prev_hash,
        miner_pubkey=legitimate_miner_pubkey,
        merkle_root=merkle_root,
        target_difficulty=2.0,
        max_iterations=5000,
    )
    assert mine_res is not None
    nonce, valid_chain = mine_res

    # Legitimate miner solution must pass verification
    ok, msg = verify_cunningham_chain(
        prev_hash=prev_hash,
        miner_pubkey=legitimate_miner_pubkey,
        merkle_root=merkle_root,
        nonce=nonce,
        chain=valid_chain,
        required_difficulty=2.0,
    )
    assert ok is True, f"Legitimate solution should verify: {msg}"

    # Attack: Attacker steals nonce and solution, but puts their own miner_pubkey
    stolen_ok, stolen_msg = verify_cunningham_chain(
        prev_hash=prev_hash,
        miner_pubkey=attacker_miner_pubkey,
        merkle_root=merkle_root,
        nonce=nonce,
        chain=valid_chain,
        required_difficulty=2.0,
    )
    # MUST FAIL because candidate origin derivation binds directly to miner_pubkey!
    assert stolen_ok is False
    assert "Origin mismatch" in stolen_msg


def test_difficulty_adjustment_rules():
    epoch_blocks = 144
    target_time = epoch_blocks * TARGET_BLOCK_TIME_SECONDS  # 8640s
    curr_diff = 4.0

    # Non-epoch height returns current difficulty
    diff_mid_epoch = calculate_next_difficulty(
        current_height=100,
        current_difficulty=curr_diff,
        epoch_start_timestamp=1000,
        epoch_end_timestamp=2000,
    )
    assert diff_mid_epoch == curr_diff

    # Exact target time at epoch boundary (height 143 -> next is 144)
    diff_exact = calculate_next_difficulty(
        current_height=143,
        current_difficulty=curr_diff,
        epoch_start_timestamp=0,
        epoch_end_timestamp=target_time,
    )
    assert diff_exact == curr_diff

    # Super fast mining: actual time 100s (much faster than 8640s)
    # Must clamp to maximum 4x increase: 4.0 * 4 = 16.0 (or MAX_DIFFICULTY 12.0)
    diff_super_fast = calculate_next_difficulty(
        current_height=143,
        current_difficulty=curr_diff,
        epoch_start_timestamp=0,
        epoch_end_timestamp=100,
    )
    assert diff_super_fast == 12.0  # Bounded by protocol MAX_DIFFICULTY

    # Very slow mining: actual time 100,000s
    # Must clamp to maximum 0.25x decrease: 4.0 * 0.25 = 1.0 -> bounded by MIN_DIFFICULTY (2.0)
    diff_super_slow = calculate_next_difficulty(
        current_height=143,
        current_difficulty=curr_diff,
        epoch_start_timestamp=0,
        epoch_end_timestamp=100000,
    )
    assert diff_super_slow == MIN_DIFFICULTY
