"""
Unit Tests for ProofCoin Blocks, Merkle Trees, and Emission Halvings.
"""

import time
import pytest
from proofcoin.core.transaction import COIN, Transaction, calculate_tx_hash
from proofcoin.core.block import (
    BlockHeader,
    Block,
    calculate_merkle_root,
    calculate_median_time_past,
    validate_block_header,
    MAX_FUTURE_BLOCK_TIME_SECONDS,
)
from proofcoin.core.chain import calculate_block_subsidy, HALVING_INTERVAL
from proofcoin.core.genesis import get_genesis_block
from proofcoin.consensus.cunningham import CunninghamChain, ChainType


def test_merkle_root_computation():
    tx1 = "11" * 32
    tx2 = "22" * 32
    tx3 = "33" * 32

    # Single leaf
    root1 = calculate_merkle_root([tx1])
    assert len(root1) == 64

    # Two leaves
    root2 = calculate_merkle_root([tx1, tx2])
    assert len(root2) == 64

    # Three leaves (odd: tx3 is duplicated to form 4-node balanced tree)
    root3 = calculate_merkle_root([tx1, tx2, tx3])
    root3_manual = calculate_merkle_root([tx1, tx2, tx3, tx3])
    assert root3 == root3_manual


def test_median_time_past_calculation():
    # 11 timestamps in chronological order
    timestamps = [100, 110, 120, 130, 140, 150, 160, 170, 180, 190, 200]
    mtp = calculate_median_time_past(timestamps)
    # Median of 11 items sorted is index 5 -> 150
    assert mtp == 150

    # Less than 11 items
    short_timestamps = [100, 200, 300]
    assert calculate_median_time_past(short_timestamps) == 200


def test_block_subsidy_halving_curve():
    # Genesis era: 50 ProofCoins
    assert calculate_block_subsidy(0) == 50 * COIN
    assert calculate_block_subsidy(209_999) == 50 * COIN

    # First halving at 210,000 blocks: 25 ProofCoins
    assert calculate_block_subsidy(210_000) == 25 * COIN

    # Second halving at 420,000 blocks: 12.5 ProofCoins
    assert calculate_block_subsidy(420_000) == 1250_000_000

    # 64th halving: subsidy reaches exact 0
    assert calculate_block_subsidy(64 * HALVING_INTERVAL) == 0


def test_block_future_timestamp_rejection():
    genesis = get_genesis_block()
    now = int(time.time())

    # Header with timestamp 3 hours into future (violates 2-hour rule)
    future_hdr = BlockHeader(
        version=1,
        prev_hash=genesis.block_hash,
        merkle_root="00" * 32,
        timestamp=now + MAX_FUTURE_BLOCK_TIME_SECONDS + 100,
        difficulty=2.0,
        nonce=1,
        miner_pubkey="02" * 32,
        solution=CunninghamChain(ChainType.FIRST_KIND, 3, 2, [3, 7]),
    )

    valid, reason = validate_block_header(
        header=future_hdr,
        prev_block_header=genesis.header,
        recent_timestamps=[genesis.header.timestamp],
        current_time=now,
    )
    assert valid is False
    assert "future" in reason.lower()
