"""
Unit Tests for ProofCoin Chain Progression and Reorganization (Reorg).
"""

import time
import pytest
from proofcoin.crypto.keys import generate_keypair
from proofcoin.crypto.address import pubkey_to_address
from proofcoin.consensus.cunningham import mine_cunningham_chain
from proofcoin.core.transaction import COIN, create_coinbase_tx
from proofcoin.core.block import BlockHeader, Block, calculate_merkle_root
from proofcoin.core.chain import Blockchain, BlockValidationResult, calculate_block_subsidy


def _mine_block(chain: Blockchain, miner_kp, prev_hash: str, height: int, difficulty: float = 2.0) -> Block:
    miner_addr = pubkey_to_address(miner_kp.public_key_hex)
    subsidy = calculate_block_subsidy(height)
    cb = create_coinbase_tx(miner_addr, subsidy, 0, height)
    mroot = calculate_merkle_root([cb.txid])

    mine_res = mine_cunningham_chain(
        prev_hash=prev_hash,
        miner_pubkey=miner_kp.public_key_hex,
        merkle_root=mroot,
        target_difficulty=difficulty,
        max_iterations=100000,
    )
    assert mine_res is not None
    nonce, solution = mine_res

    prev_block = chain.get_block_by_hash(prev_hash)
    prev_time = prev_block.header.timestamp if prev_block else 1700000000

    header = BlockHeader(
        version=1,
        prev_hash=prev_hash,
        merkle_root=mroot,
        timestamp=prev_time + 60,
        difficulty=difficulty,
        nonce=nonce,
        miner_pubkey=miner_kp.public_key_hex,
        solution=solution,
    )
    return Block(header=header, transactions=[cb])


def test_chain_linear_extension():
    chain = Blockchain()
    assert chain.height == 0
    miner_kp = generate_keypair()

    # Mine Block #1
    b1 = _mine_block(chain, miner_kp, chain.tip_block.block_hash, height=1)
    res, msg = chain.validate_and_add_block(b1)
    assert res == BlockValidationResult.VALID
    assert chain.height == 1
    assert chain.tip_block.block_hash == b1.block_hash

    # Mine Block #2
    b2 = _mine_block(chain, miner_kp, b1.block_hash, height=2)
    res, msg = chain.validate_and_add_block(b2)
    assert res == BlockValidationResult.VALID
    assert chain.height == 2
    assert chain.tip_block.block_hash == b2.block_hash


def test_chain_reorganization_to_heavier_work():
    chain = Blockchain()
    miner_a = generate_keypair()
    miner_b = generate_keypair()

    # Block 1 on shared history
    b1 = _mine_block(chain, miner_a, chain.tip_block.block_hash, height=1)
    chain.validate_and_add_block(b1)

    # Branch A: mines Block 2A
    b2_a = _mine_block(chain, miner_a, b1.block_hash, height=2)
    res_a, _ = chain.validate_and_add_block(b2_a)
    assert res_a == BlockValidationResult.VALID
    assert chain.tip_block.block_hash == b2_a.block_hash
    initial_tip_work = chain.cumulative_work

    # Branch B: mines Block 2B (fork from B1)
    b2_b = _mine_block(chain, miner_b, b1.block_hash, height=2)
    res_b, _ = chain.validate_and_add_block(b2_b)
    assert res_b == BlockValidationResult.VALID
    # Cumulative work of Branch B is equal to Branch A, so Branch A remains active tip
    assert chain.tip_block.block_hash == b2_a.block_hash

    # Branch B extends further: mines Block 3B (cumulative work now exceeds Branch A!)
    b3_b = _mine_block(chain, miner_b, b2_b.block_hash, height=3)
    res_b3, msg = chain.validate_and_add_block(b3_b)
    assert res_b3 == BlockValidationResult.VALID

    # Check Reorganization triggered!
    assert chain.tip_block.block_hash == b3_b.block_hash
    assert chain.height == 3
    assert chain.cumulative_work > initial_tip_work

    # UTXO check: Miner B received reward from block 2B and 3B
    b_addr = pubkey_to_address(miner_b.public_key_hex)
    assert chain.get_balance(b_addr) == 100 * COIN
