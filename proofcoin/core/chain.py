"""
ProofCoin Blockchain Ledger and Reorganization Engine.

Rules Enforced:
- Halving: 50 coins initially, halved every 210,000 blocks (Hard Cap: 21 Million ProofCoins).
- Reorg Rule: Highest Cumulative Proof of Useful Work (Chainwork).
- UTXO Ledger: State transitions atomic and reversible.
- Median Time Past (11 blocks) & 2-hour future timestamp barrier.
- Difficulty epoch verification (144 blocks).
"""

import time
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Set
from proofcoin.consensus.difficulty import (
    calculate_next_difficulty,
    DIFFICULTY_EPOCH_BLOCKS,
    TARGET_BLOCK_TIME_SECONDS,
)
from proofcoin.core.transaction import (
    COIN,
    MAX_MONEY,
    Transaction,
    TxOutput,
    validate_transaction_basics,
    verify_transaction_signatures,
)
from proofcoin.core.block import (
    BlockHeader,
    Block,
    calculate_merkle_root,
    calculate_median_time_past,
    validate_block_header,
)
from proofcoin.core.genesis import get_genesis_block, GENESIS_PREV_HASH

INITIAL_SUBSIDY: int = 50 * COIN
HALVING_INTERVAL: int = 210_000


def calculate_block_subsidy(height: int) -> int:
    """
    Calculate mining block reward subsidy.
    Halves every 210,000 blocks until reaching 0 atomic units.
    Total maximum emission mathematically bounded by 21,000,000 coins.
    """
    halvings = height // HALVING_INTERVAL
    if halvings >= 64:
        return 0
    return INITIAL_SUBSIDY >> halvings


class BlockValidationResult(str, Enum):
    VALID = "VALID"
    INVALID_HEADER = "INVALID_HEADER"
    INVALID_MERKLE_ROOT = "INVALID_MERKLE_ROOT"
    INVALID_COINBASE = "INVALID_COINBASE"
    INVALID_TRANSACTION = "INVALID_TRANSACTION"
    DOUBLE_SPEND = "DOUBLE_SPEND"
    INVALID_DIFFICULTY = "INVALID_DIFFICULTY"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    MISSING_PARENT = "MISSING_PARENT"


@dataclass
class ChainIndexEntry:
    """Lightweight in-memory block metadata entry."""
    block_hash: str
    height: int
    header: BlockHeader
    cumulative_work: float


class Blockchain:
    def __init__(self):
        self._blocks_by_hash: Dict[str, Block] = {}
        self._index_by_hash: Dict[str, ChainIndexEntry] = {}
        self._active_chain_hashes: List[str] = []  # Index 0 is genesis
        self._utxo_set: Dict[Tuple[str, int], TxOutput] = {}
        self._cumulative_work: float = 0.0

        # Initialize Genesis
        genesis = get_genesis_block()
        self._apply_genesis(genesis)

    @property
    def tip_block(self) -> Block:
        return self._blocks_by_hash[self._active_chain_hashes[-1]]

    @property
    def height(self) -> int:
        return len(self._active_chain_hashes) - 1

    @property
    def cumulative_work(self) -> float:
        return self._cumulative_work

    @property
    def utxo_set(self) -> Dict[Tuple[str, int], TxOutput]:
        return dict(self._utxo_set)

    def get_block_by_hash(self, block_hash: str) -> Optional[Block]:
        return self._blocks_by_hash.get(block_hash)

    def get_block_by_height(self, height: int) -> Optional[Block]:
        if 0 <= height < len(self._active_chain_hashes):
            return self._blocks_by_hash[self._active_chain_hashes[height]]
        return None

    def get_balance(self, address: str) -> int:
        """Calculate total spendable balance for an address."""
        return sum(out.amount for out in self._utxo_set.values() if out.address == address)

    def get_utxos_for_address(self, address: str) -> List[Tuple[str, int, int]]:
        """Return [(txid, vout, amount)] for an address."""
        return [
            (txid, vout, out.amount)
            for (txid, vout), out in self._utxo_set.items()
            if out.address == address
        ]

    def _apply_genesis(self, genesis: Block) -> None:
        ghash = genesis.block_hash
        self._blocks_by_hash[ghash] = genesis
        self._index_by_hash[ghash] = ChainIndexEntry(
            block_hash=ghash,
            height=0,
            header=genesis.header,
            cumulative_work=genesis.header.difficulty,
        )
        self._active_chain_hashes.append(ghash)
        self._cumulative_work = genesis.header.difficulty

        # Register genesis coinbase UTXO
        cb = genesis.transactions[0]
        for vout_idx, out in enumerate(cb.outputs):
            self._utxo_set[(cb.txid, vout_idx)] = out

    def get_recent_timestamps(self, tip_hash: str, count: int = 11) -> List[int]:
        """Collect last N timestamps along the branch starting from tip_hash."""
        timestamps = []
        curr = tip_hash
        while curr != GENESIS_PREV_HASH and len(timestamps) < count:
            if curr not in self._index_by_hash:
                break
            entry = self._index_by_hash[curr]
            timestamps.append(entry.header.timestamp)
            curr = entry.header.prev_hash
        timestamps.reverse()
        return timestamps

    def get_expected_difficulty(self, prev_hash: str) -> float:
        """Calculate the difficulty expected for the next child block of prev_hash."""
        if prev_hash not in self._index_by_hash:
            return 2.0

        prev_entry = self._index_by_hash[prev_hash]
        curr_height = prev_entry.height
        next_height = curr_height + 1

        if next_height % DIFFICULTY_EPOCH_BLOCKS != 0:
            return prev_entry.header.difficulty

        # Epoch boundary: retrieve block at epoch start
        epoch_start_height = next_height - DIFFICULTY_EPOCH_BLOCKS
        curr_hash = prev_hash
        while curr_hash in self._index_by_hash:
            item = self._index_by_hash[curr_hash]
            if item.height == epoch_start_height:
                return calculate_next_difficulty(
                    current_height=curr_height,
                    current_difficulty=prev_entry.header.difficulty,
                    epoch_start_timestamp=item.header.timestamp,
                    epoch_end_timestamp=prev_entry.header.timestamp,
                )
            curr_hash = item.header.prev_hash

        return prev_entry.header.difficulty

    def validate_and_add_block(self, block: Block) -> Tuple[BlockValidationResult, str]:
        """
        Validate block against full consensus rules and extend or reorg the active chain.
        """
        b_hash = block.block_hash
        if b_hash in self._blocks_by_hash:
            return BlockValidationResult.ALREADY_EXISTS, "Block already processed"

        # Check parent existence
        prev_hash = block.header.prev_hash
        if prev_hash not in self._index_by_hash:
            return BlockValidationResult.MISSING_PARENT, f"Parent block {prev_hash} not found in index"

        parent_entry = self._index_by_hash[prev_hash]
        parent_header = parent_entry.header
        new_height = parent_entry.height + 1

        # Verify Difficulty
        expected_diff = self.get_expected_difficulty(prev_hash)
        if abs(block.header.difficulty - expected_diff) > 0.0001:
            return BlockValidationResult.INVALID_DIFFICULTY, (
                f"Block difficulty {block.header.difficulty} does not match expected {expected_diff}"
            )

        # Validate Header (MTP, future drift, PoUW proof)
        recent_timestamps = self.get_recent_timestamps(prev_hash, 11)
        valid_hdr, reason = validate_block_header(
            header=block.header,
            prev_block_header=parent_header,
            recent_timestamps=recent_timestamps,
        )
        if not valid_hdr:
            return BlockValidationResult.INVALID_HEADER, reason

        # Verify Merkle Root
        computed_root = calculate_merkle_root([tx.txid for tx in block.transactions])
        if computed_root != block.header.merkle_root:
            return BlockValidationResult.INVALID_MERKLE_ROOT, (
                f"Merkle root mismatch: computed {computed_root}, header {block.header.merkle_root}"
            )

        # Record into blocks index
        cumulative_work = parent_entry.cumulative_work + block.header.difficulty
        self._blocks_by_hash[b_hash] = block
        self._index_by_hash[b_hash] = ChainIndexEntry(
            block_hash=b_hash,
            height=new_height,
            header=block.header,
            cumulative_work=cumulative_work,
        )

        # Check if extending current tip
        if prev_hash == self._active_chain_hashes[-1]:
            # Simple extension: validate transactions directly on current UTXO view
            success, reason = self._apply_block_to_utxo(block, new_height, commit=True)
            if not success:
                # Remove from index since it was invalid
                self._blocks_by_hash.pop(b_hash, None)
                self._index_by_hash.pop(b_hash, None)
                return BlockValidationResult.INVALID_TRANSACTION, reason

            self._active_chain_hashes.append(b_hash)
            self._cumulative_work = cumulative_work
            return BlockValidationResult.VALID, f"Block {b_hash[:8]} accepted, new height {new_height}"

        # Fork branch: check cumulative work for potential Reorganization
        if cumulative_work > self._cumulative_work:
            reorg_success, reason = self._reorganize_chain(b_hash)
            if reorg_success:
                return BlockValidationResult.VALID, f"Chain reorganized to new tip {b_hash[:8]} (work: {cumulative_work})"
            else:
                return BlockValidationResult.INVALID_TRANSACTION, f"Reorg failed: {reason}"

        return BlockValidationResult.VALID, f"Fork block {b_hash[:8]} stored (cumulative work {cumulative_work} <= current tip)"

    def _apply_block_to_utxo(
        self,
        block: Block,
        height: int,
        commit: bool = True,
        working_utxo: Optional[Dict[Tuple[str, int], TxOutput]] = None,
    ) -> Tuple[bool, str]:
        """
        Verify block transactions against UTXO ledger and update ledger.
        """
        ledger = self._utxo_set if working_utxo is None else working_utxo

        if len(block.transactions) == 0:
            return False, "Block has no transactions"

        # Rule: First transaction must be coinbase
        coinbase = block.transactions[0]
        if not coinbase.is_coinbase:
            return False, "First transaction in block is not a coinbase"

        # Rule: Only first transaction may be coinbase
        for tx in block.transactions[1:]:
            if tx.is_coinbase:
                return False, "Multiple coinbase transactions detected in block"

        # Verify normal transactions
        total_fees = 0
        txs_to_apply = []

        # Local temporary UTXO view to prevent mid-block rollback corruption
        temp_ledger = dict(ledger)

        for tx in block.transactions[1:]:
            ok_basic, reason = validate_transaction_basics(tx)
            if not ok_basic:
                return False, f"Tx {tx.txid[:8]} syntax error: {reason}"

            # Verify input signatures and existence in UTXO
            ok_sigs, reason = verify_transaction_signatures(tx, temp_ledger)
            if not ok_sigs:
                return False, f"Tx {tx.txid[:8]} validation error: {reason}"

            # Calculate fees
            in_sum = sum(temp_ledger[(inp.prev_txid, inp.vout)].amount for inp in tx.inputs)
            out_sum = sum(out.amount for out in tx.outputs)
            total_fees += (in_sum - out_sum)

            # Spend inputs in temporary ledger
            for inp in tx.inputs:
                temp_ledger.pop((inp.prev_txid, inp.vout), None)

            # Add newly created outputs in temporary ledger
            for vout_idx, out in enumerate(tx.outputs):
                temp_ledger[(tx.txid, vout_idx)] = out

        # Verify Coinbase Subsidy + Fees
        expected_subsidy = calculate_block_subsidy(height)
        max_coinbase_payout = expected_subsidy + total_fees
        coinbase_payout = sum(out.amount for out in coinbase.outputs)

        if coinbase_payout > max_coinbase_payout:
            return False, (
                f"Coinbase payout {coinbase_payout} exceeds allowed {max_coinbase_payout} "
                f"(subsidy {expected_subsidy} + fees {total_fees})"
            )

        # Register coinbase outputs in temporary ledger
        for vout_idx, out in enumerate(coinbase.outputs):
            temp_ledger[(coinbase.txid, vout_idx)] = out

        if commit and working_utxo is None:
            self._utxo_set = temp_ledger
        elif working_utxo is not None:
            working_utxo.clear()
            working_utxo.update(temp_ledger)

        return True, "Transactions verified"

    def _reorganize_chain(self, new_tip_hash: str) -> Tuple[bool, str]:
        """
        Performs chain reorganization to a branch with higher cumulative work.
        1. Identifies common ancestor.
        2. Builds candidate branch.
        3. Replays state from ancestor to new tip.
        4. If verified, updates canonical active chain.
        """
        # Step 1: Trace back new branch
        new_branch: List[str] = []
        curr = new_tip_hash
        while curr not in self._active_chain_hashes and curr != GENESIS_PREV_HASH:
            new_branch.append(curr)
            curr = self._index_by_hash[curr].header.prev_hash
        new_branch.reverse()

        common_ancestor_hash = curr
        ancestor_index = self._active_chain_hashes.index(common_ancestor_hash)

        # Step 2: Roll back UTXO set from current tip down to common ancestor
        temp_utxo = dict(self._utxo_set)
        for h in reversed(self._active_chain_hashes[ancestor_index + 1:]):
            b = self._blocks_by_hash[h]
            # Un-spend inputs, remove outputs
            for tx in reversed(b.transactions):
                for vout_idx in range(len(tx.outputs)):
                    temp_utxo.pop((tx.txid, vout_idx), None)
                if not tx.is_coinbase:
                    # In a full node, we look up spent outputs from undo-logs or block history.
                    # Here we re-populate from historical blocks
                    for inp in tx.inputs:
                        parent_tx = self._find_transaction_output(inp.prev_txid, inp.vout)
                        if parent_tx:
                            temp_utxo[(inp.prev_txid, inp.vout)] = parent_tx

        # Step 3: Apply new branch blocks forward
        curr_height = ancestor_index
        for b_hash in new_branch:
            curr_height += 1
            blk = self._blocks_by_hash[b_hash]
            valid, reason = self._apply_block_to_utxo(blk, curr_height, commit=False, working_utxo=temp_utxo)
            if not valid:
                return False, f"Reorg validation failed at block {b_hash[:8]}: {reason}"

        # Step 4: Commit Reorganization
        self._utxo_set = temp_utxo
        self._active_chain_hashes = self._active_chain_hashes[:ancestor_index + 1] + new_branch
        self._cumulative_work = self._index_by_hash[new_tip_hash].cumulative_work
        return True, "Reorganization committed"

    def _find_transaction_output(self, txid: str, vout: int) -> Optional[TxOutput]:
        """Search transaction history for an output (used for reorg rollbacks)."""
        for blk in self._blocks_by_hash.values():
            for tx in blk.transactions:
                if tx.txid == txid and 0 <= vout < len(tx.outputs):
                    return tx.outputs[vout]
        return None
