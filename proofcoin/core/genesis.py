"""
ProofCoin Genesis Block Definition.

Establishes the immutable root of the ProofCoin ledger:
- Height: 0
- Previous Block Hash: 64 zeros
- Genesis Block Reward: 50.00 ProofCoins (5,000,000,000 atomic units)
- Canonical timestamp: 1700000000 (2023-11-14 22:13:20 UTC)
- Difficulty: 2.0
"""

from typing import Optional
from proofcoin.crypto.address import pubkey_to_address
from proofcoin.consensus.cunningham import (
    CunninghamChain,
    ChainType,
    mine_cunningham_chain,
)
from proofcoin.core.transaction import (
    COIN,
    Transaction,
    create_coinbase_tx,
)
from proofcoin.core.block import BlockHeader, Block, calculate_merkle_root

GENESIS_PREV_HASH: str = "00" * 32
GENESIS_TIMESTAMP: int = 1700000000
GENESIS_MINER_PUBKEY: str = "02" * 32
GENESIS_INITIAL_DIFFICULTY: float = 2.0

_cached_genesis_block: Optional[Block] = None


def get_genesis_block() -> Block:
    """
    Constructs or retrieves the cached canonical Genesis Block.
    """
    global _cached_genesis_block
    if _cached_genesis_block is not None:
        return _cached_genesis_block

    genesis_address = pubkey_to_address(GENESIS_MINER_PUBKEY)
    coinbase_tx = create_coinbase_tx(
        recipient_address=genesis_address,
        block_reward=50 * COIN,
        fees=0,
        height=0,
    )

    merkle_root = calculate_merkle_root([coinbase_tx.txid])

    # Mine deterministic genesis solution if not pre-seeded
    mining_result = mine_cunningham_chain(
        prev_hash=GENESIS_PREV_HASH,
        miner_pubkey=GENESIS_MINER_PUBKEY,
        merkle_root=merkle_root,
        target_difficulty=GENESIS_INITIAL_DIFFICULTY,
        start_nonce=0,
        max_iterations=10000,
    )

    if not mining_result:
        raise RuntimeError("Failed to compute valid genesis PoUW chain")

    nonce, solution = mining_result

    header = BlockHeader(
        version=1,
        prev_hash=GENESIS_PREV_HASH,
        merkle_root=merkle_root,
        timestamp=GENESIS_TIMESTAMP,
        difficulty=GENESIS_INITIAL_DIFFICULTY,
        nonce=nonce,
        miner_pubkey=GENESIS_MINER_PUBKEY,
        solution=solution,
    )

    _cached_genesis_block = Block(
        header=header,
        transactions=[coinbase_tx],
    )
    return _cached_genesis_block
